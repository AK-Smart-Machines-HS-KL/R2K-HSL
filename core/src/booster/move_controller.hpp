#ifndef __BOOSTER_ROBOTICS_SDK_MOVE_CONTROLLER_HPP__
#define __BOOSTER_ROBOTICS_SDK_MOVE_CONTROLLER_HPP__

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>

#include <booster/idl/b1/Odometer.h>
#include <booster/robot/b1/b1_api_const.hpp>
#include <booster/robot/b1/b1_loco_client.hpp>
#include <booster/robot/channel/channel_factory.hpp>
#include <booster/robot/channel/channel_subscriber.hpp>
#include <booster/robot/rpc/error.hpp>

namespace booster {
namespace robot {
namespace b1 {

/**
 * @file move_controller.hpp
 * @brief Blocking planar-position helper built on B1LocoClient and odometry.
 */

/**
 * @brief Drives the robot to simple planar translation and rotation targets.
 *
 * The controller subscribes to kTopicOdometerState and repeatedly streams
 * velocity commands through B1LocoClient::MoveCommand(). Construction waits
 * for odometry, resets the odometry origin, and may block for several seconds.
 * Translation methods use the reset odometry frame; they do not provide path
 * planning or obstacle avoidance.
 *
 * @note Supported model: K1 | T1 | T2
 * @warning The movement methods are blocking. MoveToTarget() and
 * MoveToRelative() have no overall progress timeout and should be supervised
 * by the application.
 */
class MoveController {
public:
    /**
     * @brief Initializes transport, odometry tracking, and the locomotion client.
     *
     * The constructor waits up to five seconds for odometry, then retries
     * ResetOdometry() up to five times. A reset failure is logged but does not
     * fail construction.
     *
     * @param ip Network interface name or address accepted by ChannelFactory;
     * an empty string selects the default interface.
     * @throws std::runtime_error If no odometry message is received within
     * five seconds.
     * @note Other exceptions raised by channel initialization are propagated.
     */
    explicit MoveController(const std::string &ip = "") {
        try {
            ChannelFactory::Instance()->Init(0, ip);
            client_.Init();

            tracker_.InitChannel();
            WaitForTrackerReady(std::chrono::seconds(5));
            std::this_thread::sleep_for(std::chrono::seconds(2));

            if (!RetryApiCall([this]() { return client_.ResetOdometry(); },
                              "ResetOdometry",
                              5,
                              std::chrono::seconds(1))) {
                std::cerr << "[ERROR] ResetOdometry failed after retries."
                          << std::endl;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        } catch (...) {
            tracker_.CloseChannel();
            is_closed_ = true;
            throw;
        }
    }

    /** @brief Stops motion and closes the odometry subscriber. */
    ~MoveController() {
        Close();
    }

    /** @brief MoveController instances cannot be copied. */
    MoveController(const MoveController &) = delete;

    /** @brief MoveController instances cannot be copy-assigned. */
    MoveController &operator=(const MoveController &) = delete;

    /** @brief MoveController instances cannot be moved. */
    MoveController(MoveController &&) = delete;

    /** @brief MoveController instances cannot be move-assigned. */
    MoveController &operator=(MoveController &&) = delete;

    /**
     * @brief Moves to an absolute point in the current odometry frame.
     *
     * The controller first turns toward a distant target, then translates
     * while holding the current heading. Success is declared within 0.20 m of
     * the target.
     *
     * @param x Target x coordinate in metres.
     * @param y Target y coordinate in metres.
     * @param vel Positive maximum planar speed in metres per second.
     * @return `true` after reaching the tolerance; `false` if an exception is
     * raised while reading odometry or sending commands.
     * @warning This method has no overall timeout. A non-positive `vel`, a
     * blocked robot, or stale-but-readable odometry can prevent it from
     * returning.
     */
    bool MoveToTarget(float x, float y, float vel) {
        constexpr float kDistanceTolerance = 0.20f;

        try {
            const auto rotation_start = std::chrono::steady_clock::now();
            while (true) {
                auto [cur_x, cur_y, cur_theta] = tracker_.GetPose();
                const float dist = std::hypot(x - cur_x, y - cur_y);
                const auto elapsed = std::chrono::steady_clock::now() - rotation_start;

                if (dist < 0.6f || elapsed > std::chrono::seconds(5)) {
                    break;
                }

                const float target_heading = std::atan2(y - cur_y, x - cur_x);
                const float heading_error = NormalizeAngle(target_heading - cur_theta);
                if (std::fabs(heading_error) < 0.2f) {
                    break;
                }

                const float vyaw = std::clamp(1.2f * heading_error, -1.0f, 1.0f);
                SafeMove(0.0f, 0.0f, vyaw);
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            }

            SafeMove(0.0f, 0.0f, 0.0f);

            const float hold_theta = std::get<2>(tracker_.GetPose());

            while (true) {
                auto [cur_x, cur_y, cur_theta] = tracker_.GetPose();
                const float dx = x - cur_x;
                const float dy = y - cur_y;
                const float dist = std::hypot(dx, dy);

                if (dist < kDistanceTolerance) {
                    Stop();
                    return true;
                }

                const float cos_theta = std::cos(cur_theta);
                const float sin_theta = std::sin(cur_theta);
                float vx = dx * cos_theta + dy * sin_theta;
                float vy = -dx * sin_theta + dy * cos_theta;

                float local_limit = vel;
                if (dist < 0.2f) {
                    local_limit = std::max(0.1f, dist);
                    if (dist < 0.1f) {
                        local_limit = std::max(0.05f, local_limit);
                    }
                }

                const float current_speed = std::hypot(vx, vy);
                if (current_speed > local_limit && current_speed > 1e-6f) {
                    const float scale = local_limit / current_speed;
                    vx *= scale;
                    vy *= scale;
                }

                const float vyaw =
                    std::clamp(NormalizeAngle(hold_theta - cur_theta), -0.5f, 0.5f);
                SafeMove(vx, vy, vyaw);

                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            }
        } catch (...) {
            Stop();
            return false;
        }
    }

    /**
     * @brief Moves by an offset from the current odometry position.
     *
     * The offset is added in odometry-frame axes, not rotated by the robot's
     * current heading.
     *
     * @param dx X offset in metres in the odometry frame.
     * @param dy Y offset in metres in the odometry frame.
     * @param vel Positive maximum planar speed in metres per second.
     * @return The result of MoveToTarget().
     */
    bool MoveToRelative(float dx, float dy, float vel) {
        const auto pose = tracker_.GetPose();
        const float cur_x = std::get<0>(pose);
        const float cur_y = std::get<1>(pose);
        return MoveToTarget(cur_x + dx, cur_y + dy, vel);
    }

    /**
     * @brief Rotates by an accumulated yaw angle.
     *
     * Rotation is measured by integrating wrapped odometry-yaw changes, which
     * permits requests larger than one revolution.
     *
     * @param angle Requested rotation magnitude in radians. With the current
     * controller convention, a positive value produces a negative yaw command
     * and a negative value produces a positive yaw command.
     * @param vel Yaw-speed magnitude in radians per second; the absolute value
     * is used.
     * @return `true` after accumulating the requested angle; `false` if an
     * exception occurs.
     * @warning A zero velocity with a non-zero angle can block indefinitely.
     */
    bool TurnAround(float angle, float vel) {
        const float direction_sign = angle > 0.0f ? -1.0f : 1.0f;
        const float target_accumulated = std::fabs(angle);
        const float vel_mag = std::fabs(vel);
        float current_accumulated = 0.0f;
        float last_theta = std::get<2>(tracker_.GetPose());

        try {
            while (true) {
                const float curr_theta = std::get<2>(tracker_.GetPose());
                const float delta = NormalizeAngle(curr_theta - last_theta);
                current_accumulated += std::fabs(delta);
                last_theta = curr_theta;

                const float remaining = target_accumulated - current_accumulated;
                if (remaining <= 0.0f) {
                    Stop();
                    return true;
                }

                float cmd_vel = vel_mag;
                if (remaining < 0.2f) {
                    cmd_vel = std::max(0.2f, remaining * 2.0f);
                }

                SafeMove(0.0f, 0.0f, direction_sign * cmd_vel);

                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            }
        } catch (...) {
            Stop();
            return false;
        }
    }

    /**
     * @brief Sends a zero planar-velocity command.
     * @note The command uses fire-and-forget transport; it does not wait for a
     * robot response.
     */
    void Stop() {
        SafeMove(0.0f, 0.0f, 0.0f);
    }

    /**
     * @brief Stops the robot and releases the odometry subscription.
     *
     * This method is idempotent. No movement method should be called after
     * Close().
     */
    void Close() {
        if (is_closed_) {
            return;
        }

        Stop();
        tracker_.CloseChannel();
        is_closed_ = true;
    }

private:
    class PoseTracker {
    public:
        PoseTracker() :
            channel_subscriber_(
                kTopicOdometerState,
                [this](const void *msg) { HandleMessage(msg); }) {
        }

        void InitChannel() {
            channel_subscriber_.InitChannel();
        }

        void CloseChannel() {
            channel_subscriber_.CloseChannel();
        }

        bool Ready() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return ready_;
        }

        std::tuple<float, float, float> GetPose() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return std::make_tuple(x_, y_, theta_);
        }

    private:
        void HandleMessage(const void *msg) {
            const auto *odom =
                static_cast<const booster_interface::msg::Odometer *>(msg);
            std::lock_guard<std::mutex> lock(mutex_);
            x_ = odom->x();
            y_ = odom->y();
            theta_ = odom->theta();
            ready_ = true;
        }

    private:
        mutable std::mutex mutex_;
        float x_{0.0f};
        float y_{0.0f};
        float theta_{0.0f};
        bool ready_{false};
        ChannelSubscriber<booster_interface::msg::Odometer> channel_subscriber_;
    };

private:
    template <typename Func>
    bool RetryApiCall(Func &&func,
                      const std::string &description,
                      int max_retries,
                      std::chrono::milliseconds delay) {
        for (int attempt = 0; attempt < max_retries; ++attempt) {
            const int32_t ret = func();
            if (ret == kRpcStatusCodeSuccess) {
                return true;
            }
            if (ret == kRpcStatusCodeTimeout) {
                std::cerr << "[WARN] '" << description
                          << "' failed (RPC Timeout 100). Retrying "
                          << (attempt + 1) << "/" << max_retries << "..."
                          << std::endl;
                std::this_thread::sleep_for(delay);
                continue;
            }
            std::cerr << "[ERROR] '" << description
                      << "' failed, code = " << ret << std::endl;
            return false;
        }
        return false;
    }

    void SafeMove(float vx, float vy, float vyaw) {
        const int32_t ret = client_.MoveCommand(vx, vy, vyaw);
        if (ret == kRpcStatusCodeSuccess || ret == kRpcStatusCodeTimeout) {
            if (ret == kRpcStatusCodeTimeout) {
                std::cerr << "[WARN] Move command send timeout (code 100). Packet dropped, continuing..."
                          << std::endl;
            }
            return;
        }
        std::cerr << "[ERROR] Move command failed, code = " << ret << std::endl;
    }

    void WaitForTrackerReady(std::chrono::milliseconds timeout) {
        const auto start = std::chrono::steady_clock::now();
        while (!tracker_.Ready()) {
            if (std::chrono::steady_clock::now() - start > timeout) {
                throw std::runtime_error("Odometer not responding.");
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }

    static float NormalizeAngle(float angle) {
        constexpr float kPi = 3.14159265358979323846f;
        constexpr float kTwoPi = 2.0f * kPi;
        while (angle > kPi) {
            angle -= kTwoPi;
        }
        while (angle < -kPi) {
            angle += kTwoPi;
        }
        return angle;
    }

private:
    B1LocoClient client_;
    PoseTracker tracker_;
    bool is_closed_{false};
};

}
}
} // namespace booster::robot::b1

#endif // __BOOSTER_ROBOTICS_SDK_MOVE_CONTROLLER_HPP__
