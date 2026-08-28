#ifndef __BOOSTER_ROBOTICS_SDK_B1_LOCO_API_HPP__
#define __BOOSTER_ROBOTICS_SDK_B1_LOCO_API_HPP__

#include <string>
#include <booster/third_party/nlohmann_json/json.hpp>
#include <booster/robot/common/device_info.hpp>
#include <booster/robot/b1/b1_api_const.hpp>
#include <booster/robot/common/entities.hpp>
#include <booster/robot/common/robot_shared.hpp>

namespace booster {
namespace robot {
namespace b1 {

/**
 * @file b1_loco_api.hpp
 * @brief Data types and RPC identifiers for the B1 locomotion service.
 *
 * This header defines the wire-level request and response objects used by
 * B1LocoClient. Parameter objects can be serialized with ToJson() and response
 * objects can be populated with FromJson(). Unless stated otherwise, angles are
 * expressed in radians, distances in metres, and durations in milliseconds.
 *
 * @note The JSON conversion functions use nlohmann::json and may throw a
 * nlohmann::json::exception when a required field is missing or has an
 * incompatible type.
 *
 * @anchor b1_loco_model_support_matrix
 * @par Model support and runtime capability detection
 * Unless an operation or option is listed below, supported model: K1 | T1 | T2.
 * Some capabilities are selected by the factory software
 * configuration and cannot be queried as individual switches through this SDK.
 * Applications should use the RPC result: kRpcStatusCodeServerRefused means
 * that the capability is disabled for the installed configuration, while
 * kRpcStatusCodeStateTransitionFailed means that the requested motion is not
 * available from the robot's current state or software graph.
 * Hardware-dependent hand operations additionally require the corresponding
 * device to be reported by B1LocoClient::GetHands().
 *
 * @note The current T1_7DofArm factory configuration disables the shared action
 * capability used by WaveHand, Handshake, GetUp, GetUpWithMode, LieDown,
 * PushUp, and Dance. These calls return kRpcStatusCodeServerRefused, which is
 * the application-visible way to detect this configuration.
 *
 * This table is the authoritative model-capability summary for the B1
 * locomotion API. Per-type and per-method documentation links here and retains
 * only operation-specific usage or safety information.
 *
 * | Operation or option | Supported models | Restrictions |
 * | --- | --- | --- |
 * | RobotMode::kSoccer | K1, T1 | Soccer mode is disabled on T2. |
 * | LocoApiId::kWaveHand | K1, T1, T2 | T2 supports start only; a manual stop request is refused. |
 * | LocoApiId::kLieDown | K1, T1, T2 | Availability follows the factory action configuration; disabled configurations return kRpcStatusCodeServerRefused. T1 has a lie-down trajectory and T2 has a model-specific trajectory. K1 currently accepts the request, but all of its configured nested-trajectory slots are placeholders; it can return success while commanding a non-lie-down zero-position trajectory. |
 * | GetUpVersion::kV1 | K1, T1, T2 | Applies to both get-up operations. |
 * | GetUpVersion::kV2 | K1 | Requests using this value are refused on T1 and T2. |
 * | LocoApiId::kHandshake | K1, T1, T2 | No model-name gate. A disabled factory action capability returns kRpcStatusCodeServerRefused; an unavailable action transition returns kRpcStatusCodeStateTransitionFailed. The current T1_7DofArm configuration is refused. |
 * | Biped hand-planner operations | Configuration-dependent | The current K1 and T1 factory software provides these operations; handlers do not reject other models by name. A missing or unreachable planner action returns kRpcStatusCodeStateTransitionFailed. Dance returns kRpcStatusCodeServerRefused first when the shared action capability is disabled. Stopping an inactive planner returns kRpcStatusCodeBadRequest. |
 * | LocoApiId::kPushUp | Configuration-dependent | No public B1LocoClient convenience method. Generic RPC dispatches a model-configured nested trajectory. A disabled action capability returns kRpcStatusCodeServerRefused; an unavailable trajectory can fail or execute a configured placeholder. |
 * | LocoApiId::kShoot | Configuration-dependent | No model-name gate. A model without the required reachable motion returns kRpcStatusCodeStateTransitionFailed. |
 * | WholeBodyDanceId values 0 through 9 | K1 | T1 supports no whole-body dance IDs. |
 * | WholeBodyDanceId::kBowAndArrow, WholeBodyDanceId::kCharlestonDance | T2 | T1 supports no whole-body dance IDs. |
 * | Custom trained-trajectory load/activate/unload | K1, T2 | T1 has no trained-trajectory body controller. |
 * | EnterWBCGait / ExitWBCGait | Configuration-dependent | No model-name gate. If the configured gait motion is absent or cannot be entered, the call returns kRpcStatusCodeStateTransitionFailed. Current K1 factory software provides the WBC gait path. |
 * | Lion-dance operations | Configuration-dependent | The current K1 factory software provides the required motions; handlers do not reject other models by name. A missing or unreachable required motion normally returns kRpcStatusCodeStateTransitionFailed. A failed arm-fix precondition can instead return kRpcStatusCodeInternalServerError. LionDancePrepare can acknowledge an asynchronous intermediate transition before the final pose is entered. |
 * | GaitType values | Configuration-dependent | Each value maps to a body control. Current graphs make kHalfBodyHumanlikeGaitV2 broadly available and the other values primarily K1 capabilities; missing controls return kRpcStatusCodeStateTransitionFailed. |
 * | VisualKickVersion values | Configuration-dependent | No model-name gate. kV1 requests the base visual-kick path. Where the factory software does not enable the WBC gait path, kV2 falls back to the configured non-WBC path instead of being rejected solely by version. Missing or unreachable motions return kRpcStatusCodeStateTransitionFailed. |
 * | LocoApiId::kHandOnChestGreeting | T2 | Requests are rejected on K1 and T1. |
 * | LocoApiId::kSwitchHandEndEffectorControlMode | Backend-dependent | The robot-state-manager RPC handler does not implement this ID and returns kRpcStatusCodeBadRequest. The legacy LocoApiService on the same topic does implement it. |
 *
 * @see B1LocoClient
 */

/** @brief RPC service name used by the B1 locomotion client. */
const std::string LOCO_SERVICE_NAME = "loco";

/** @brief Version of the B1 locomotion RPC API described by this header. */
const std::string LOCO_API_VERSION = "1.0.0.1";

/**
 * @brief Numeric identifiers for B1 locomotion RPC operations.
 *
 * Applications normally call the corresponding convenience method on
 * B1LocoClient. These identifiers are exposed for users of the generic
 * SendApiRequest APIs and for protocol diagnostics.
 */
enum class LocoApiId {
    kChangeMode = 2000,                       ///< Change mode; soccer mode supported model: K1 | T1.
    kMove = 2001,                             ///< Command planar linear and angular velocity.
    kRotateHead = 2004,                       ///< Rotate the head to a target pitch and yaw.
    kWaveHand = 2005,                         ///< Wave a hand; supported model: K1 | T1 | T2. T2 supports start only.
    kRotateHeadWithDirection = 2006,          ///< Rotate the head continuously by direction.
    kLieDown = 2007,                          ///< Dispatch model-configured lie-down slot; see the K1 safety warning above.
    kGetUp = 2008,                            ///< Get up; supported model: K1 | T1 | T2. Version kV2 supported model: K1.
    kMoveHandEndEffector = 2009,              ///< Move one hand end effector; supported model: K1 | T1.
    kControlGripper = 2010,                   ///< Control a gripper attached to either hand.
    kGetFrameTransform = 2011,                ///< Query a transform between robot frames.
    kSwitchHandEndEffectorControlMode = 2012, ///< Legacy-service operation; not handled by robot-state-manager RPC.
    kControlDexterousHand = 2013,             ///< Control individual dexterous-hand fingers.
    kHandshake = 2015,                        ///< Start or stop a factory-enabled handshake action.
    kDance = 2016,                            ///< Run an upper-body dance or gesture; supported model: K1 | T1.
    kGetMode = 2017,                          ///< Query the current robot mode.
    kGetStatus = 2018,                        ///< Query mode, body-control, and action status.
    kPushUp = 2019,                           ///< Generic-RPC-only nested trajectory; B1LocoClient has no PushUp() wrapper.
    kPlaySound = 2020,                        ///< Play an audio file on the robot.
    kStopSound = 2021,                        ///< Stop the currently playing audio.
    kGetRobotInfo = 2022,                     ///< Query robot identity and firmware information.
    kStopHandEndEffector = 2023,              ///< Stop hand end-effector motion; supported model: K1 | T1.
    kShoot = 2024,                            ///< Request the configured shooting motion; unavailable transitions fail.
    kGetUpWithMode = 2025,                    ///< Get up into a mode; see GetUpVersion support.
    kZeroTorqueDrag = 2026,                   ///< Enable or disable zero-torque drag; supported model: K1 | T1.
    kRecordTrajectory = 2027,                 ///< Start or stop trajectory recording; supported model: K1 | T1.
    kReplayTrajectory = 2028,                 ///< Replay a recorded trajectory; supported model: K1 | T1.
    kWholeBodyDance = 2029,                   ///< Run a model-specific whole-body trajectory.
    kUpperBodyCustomControl = 2030,           ///< Start or stop upper-body custom control.
    kResetOdometry = 2031,                    ///< Reset the robot odometry origin.
    kLoadCustomTrainedTraj = 2032,            ///< Load a custom trained trajectory; supported model: K1 | T2.
    kActivateCustomTrainedTraj = 2033,        ///< Activate a trained trajectory; supported model: K1 | T2.
    kUnloadCustomTrainedTraj = 2034,          ///< Unload a trained trajectory; supported model: K1 | T2.
    kEnterWBCGait = 2035,                     ///< Enter the configured WBC gait; unavailable transitions fail.
    kExitWBCGait = 2036,                      ///< Exit to the configured humanlike gait; unavailable transitions fail.
    kMoveDualHandEndEffector = 2037,          ///< Move both hand end effectors; supported model: K1 | T1.
    kVisualKick = 2038,                       ///< Run visual kick using configured primary or fallback controls.
    kLionDancePrepare = 2039,                 ///< Enter or leave lion-dance preparation; supported model: K1.
    kLionDanceStart = 2040,                   ///< Start a lion-dance routine; supported model: K1.
    kLionDanceMove = 2041,                    ///< Start or stop lion-dance locomotion; supported model: K1.
    kSwitchGait = 2042,                       ///< Select a mapped body control; missing controls fail state transition.
    kRotateHeadWithTime = 2043,               ///< Rotate the head over a requested duration.
    kGetSensors = 2044,                       ///< Query the configured IMU sensor catalog.
    kGetHands = 2045,                         ///< Query the configured hand catalog.
    kGetRobotModel = 2046,                    ///< Query the static robot model.
    kGetTrainedTrajStatus = 2047,             ///< Query trained-trajectory execution status.
    kHandOnChestGreeting = 2050,              ///< Raise or lower the chest greeting; supported model: T2.
};

/**
 * @brief Available humanlike gait implementations.
 * @note The RPC handler does not gate these values by model. Each value maps to
 * a body control in the active state graph. Current configurations broadly
 * provide kHalfBodyHumanlikeGaitV2, while the other values are primarily K1
 * capabilities. If the mapped control cannot be selected, the service returns
 * kRpcStatusCodeStateTransitionFailed.
 */
enum class GaitType {
    kWholeBodyHumanlikeGait = 0,   ///< Whole-body gait currently configured primarily on K1.
    kHalfBodyHumanlikeGait = 1,    ///< Legacy half-body gait currently configured primarily on K1.
    kHalfBodyHumanlikeGaitV2 = 2,  ///< Updated half-body gait broadly available in current configurations.
    kWholeBodyHumanlikeGaitV2 = 3, ///< Updated whole-body gait currently configured primarily on K1.
};

/**
 * @brief Request payload for rotating the head to a target orientation.
 *
 * The target is expressed as pitch and yaw angles relative to the robot's
 * neutral head orientation.
 */
class RotateHeadParameter {
public:
    /** @brief Constructs an empty payload; members are not initialized. */
    RotateHeadParameter() = default;

    /**
     * @brief Constructs a head-rotation request.
     * @param pitch Target pitch angle in radians.
     * @param yaw Target yaw angle in radians.
     */
    RotateHeadParameter(float pitch, float yaw) :
        pitch_(pitch),
        yaw_(yaw) {
    }

public:
    /**
     * @brief Populates this request from a JSON object.
     * @param json JSON object containing numeric `pitch` and `yaw` fields.
     */
    void FromJson(nlohmann::json &json) {
        pitch_ = json["pitch"];
        yaw_ = json["yaw"];
    }

    /**
     * @brief Serializes this request to its RPC JSON representation.
     * @return JSON object containing `pitch` and `yaw`.
     */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["pitch"] = pitch_;
        json["yaw"] = yaw_;
        return json;
    }

public:
    float pitch_; ///< Target pitch angle in radians.
    float yaw_;   ///< Target yaw angle in radians.
};

/** @brief Request payload for timed head rotation. */
class RotateHeadWithTimeParameter {
public:
    /** @brief Constructs an empty payload; members are not initialized. */
    RotateHeadWithTimeParameter() = default;

    /**
     * @brief Constructs a timed head-rotation request.
     * @param pitch Target pitch angle in radians.
     * @param yaw Target yaw angle in radians.
     * @param time_millis Time allowed to reach the target, in milliseconds.
     */
    RotateHeadWithTimeParameter(float pitch, float yaw, int time_millis) :
        pitch_(pitch),
        yaw_(yaw),
        time_millis_(time_millis) {
    }

public:
    /**
     * @brief Populates this request from JSON.
     * @param json JSON object containing `pitch`, `yaw`, and `time_millis`.
     */
    void FromJson(nlohmann::json &json) {
        pitch_ = json["pitch"];
        yaw_ = json["yaw"];
        time_millis_ = json["time_millis"];
    }

    /**
     * @brief Serializes this request to JSON.
     * @return JSON object containing the target angles and duration.
     */
    nlohmann::json ToJson() const {
        nlohmann::json json;

        json["pitch"] = pitch_;
        json["yaw"] = yaw_;
        json["time_millis"] = time_millis_;
        return json;
    }

public:
    float pitch_;    ///< Target pitch angle in radians.
    float yaw_;      ///< Target yaw angle in radians.
    int time_millis_; ///< Requested motion duration in milliseconds.
};

/**
 * @brief Request payload for changing the robot operating mode.
 * @note Supported model: K1 | T1 | T2
 * @note RobotMode::kSoccer supported model: K1 | T1
 */
class ChangeModeParameter {
public:
    /** @brief Constructs an empty payload; mode_ is not initialized. */
    ChangeModeParameter() = default;

    /** @brief Constructs a mode-change request. @param mode Target robot mode. */
    ChangeModeParameter(booster::robot::RobotMode mode) :
        mode_(mode) {
    }

public:
    /** @brief Populates this request from a JSON `mode` value. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        mode_ = static_cast<booster::robot::RobotMode>(json["mode"]);
    }

    /** @brief Serializes the target mode. @return JSON object containing integer field `mode`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["mode"] = static_cast<int>(mode_);
        return json;
    }

public:
    booster::robot::RobotMode mode_; ///< Target robot operating mode.
};

/**
 * @brief Request payload for selecting a humanlike gait implementation.
 * @note Availability is determined by the selected GaitType value and the
 * active robot software configuration.
 */
class SwitchGaitParameter {
public:
    /** @brief Constructs a request for the default whole-body gait. */
    SwitchGaitParameter() = default;

    /** @brief Constructs a gait-switch request. @param gait_type Target gait implementation. */
    SwitchGaitParameter(GaitType gait_type) :
        gait_type_(gait_type) {
    }

public:
    /** @brief Populates this request from JSON field `gait_type`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        gait_type_ = static_cast<GaitType>(json["gait_type"]);
    }

    /** @brief Serializes the gait selection. @return JSON object containing `gait_type`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["gait_type"] = static_cast<int>(gait_type_);
        return json;
    }

public:
    GaitType gait_type_ = GaitType::kWholeBodyHumanlikeGait; ///< Target gait implementation.
};

/** @brief Response payload returned by the get-mode operation. */
class GetModeResponse {
public:
    /** @brief Constructs an empty response; mode_ is not initialized. */
    GetModeResponse() = default;

public:
    /** @brief Parses the response JSON field `mode`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        mode_ = static_cast<booster::robot::RobotMode>(json["mode"]);
    }

    /** @brief Serializes this response. @return JSON object containing integer field `mode`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["mode"] = static_cast<int>(mode_);
        return json;
    }

public:
    booster::robot::RobotMode mode_; ///< Current robot operating mode.
};

/**
 * @brief Response payload describing the robot's current locomotion status.
 *
 * The response reports the active operating mode, body controller, and any
 * currently executing high-level actions.
 */
class GetStatusResponse {
public:
    /** @brief Constructs an empty response; scalar members are not initialized. */
    GetStatusResponse() = default;

    /**
     * @brief Populates this response from JSON.
     * @param json JSON object containing `current_mode`, `current_body_control`,
     * and an array named `current_actions`.
     */
    void FromJson(nlohmann::json &json) {
        current_mode_ = static_cast<booster::robot::RobotMode>(json["current_mode"]);
        current_body_control_ = static_cast<booster::robot::BodyControl>(json["current_body_control"]);
        std::vector<booster::robot::Action> actions_vec;
        for (const auto &item : json["current_actions"]) {
            actions_vec.push_back(static_cast<booster::robot::Action>(item));
        }
        current_actions_ = std::move(actions_vec);
    }

    /**
     * @brief Serializes this status response.
     * @return JSON object containing mode, body-control, and action values.
     */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["current_mode"] = static_cast<int>(current_mode_);
        json["current_body_control"] = static_cast<int>(current_body_control_);
        std::vector<int> actions_int_vec;
        for (const auto &action : current_actions_) {
            actions_int_vec.push_back(static_cast<int>(action));
        }
        json["current_actions"] = actions_int_vec;
        return json;
    }

public:
    booster::robot::RobotMode current_mode_; ///< Current robot operating mode.
    booster::robot::BodyControl current_body_control_; ///< Active body-control implementation.
    std::vector<booster::robot::Action> current_actions_; ///< High-level actions currently running.
};

/** @brief Response payload containing robot identity and firmware metadata. */
class GetRobotInfoResponse {
public:
    /** @brief Constructs an empty robot-information response. */
    GetRobotInfoResponse() = default;

    /**
     * @brief Populates all robot-information fields from JSON.
     * @param json JSON object containing `name`, `nickname`, `version`, `model`,
     * `serial_number`, `edition`, and `region`.
     */
    void FromJson(nlohmann::json &json) {
        name_ = json["name"];
        nickname_ = json["nickname"];
        version_ = json["version"];
        model_ = json["model"];
        serial_number_ = json["serial_number"];
        edition_ = json["edition"];
        region_ = json["region"];
    }

    /** @brief Serializes all robot-information fields. @return Robot-information JSON object. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["name"] = name_;
        json["nickname"] = nickname_;
        json["version"] = version_;
        json["model"] = model_;
        json["serial_number"] = serial_number_;
        json["edition"] = edition_;
        json["region"] = region_;
        return json;
    }

public:
    std::string name_;          ///< Official robot name.
    std::string nickname_;      ///< User-defined nickname configured in the Booster mobile app.
    std::string version_;       ///< Robot firmware version.
    std::string model_;         ///< Robot model name.
    std::string serial_number_; ///< Robot serial number.
    std::string edition_;       ///< Product edition, for example `K1 ...` or `T1 ...`.
    std::string region_;        ///< Product region, for example `CN` or `Global`.
};

/** @brief Request payload for planar robot velocity control. */
class MoveParameter {
public:
    /** @brief Constructs an empty payload; velocity members are not initialized. */
    MoveParameter() = default;

    /**
     * @brief Constructs a planar velocity request.
     * @param vx Forward linear velocity in metres per second.
     * @param vy Lateral linear velocity in metres per second.
     * @param vyaw Yaw angular velocity in radians per second.
     */
    MoveParameter(float vx, float vy, float vyaw) :
        vx_(vx),
        vy_(vy),
        vyaw_(vyaw) {
    }

public:
    /**
     * @brief Populates this request from JSON.
     * @param json JSON object containing numeric `vx`, `vy`, and `vyaw` fields.
     */
    void FromJson(nlohmann::json &json) {
        vx_ = json["vx"];
        vy_ = json["vy"];
        vyaw_ = json["vyaw"];
    }

    /** @brief Serializes the velocity command. @return JSON object containing `vx`, `vy`, and `vyaw`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["vx"] = vx_;
        json["vy"] = vy_;
        json["vyaw"] = vyaw_;
        return json;
    }

public:
    float vx_;   ///< Forward linear velocity in metres per second.
    float vy_;   ///< Lateral linear velocity in metres per second.
    float vyaw_; ///< Yaw angular velocity in radians per second.
};

/**
 * @brief Request payload for continuous, direction-based head rotation.
 *
 * Each direction is conventionally one of `-1`, `0`, or `1`. A zero value
 * stops motion about that axis. See B1LocoClient::RotateHeadWithDirection() for
 * the direction mapping used by the client API.
 */
class RotateHeadWithDirectionParameter {
public:
    /** @brief Constructs an empty payload; members are not initialized. */
    RotateHeadWithDirectionParameter() = default;

    /**
     * @brief Constructs a direction-based head request.
     * @param pitch_direction Pitch-axis direction (`-1`, `0`, or `1`).
     * @param yaw_direction Yaw-axis direction (`-1`, `0`, or `1`).
     */
    RotateHeadWithDirectionParameter(int pitch_direction, int yaw_direction) :
        pitch_direction_(pitch_direction),
        yaw_direction_(yaw_direction) {
    }

public:
    /** @brief Populates this request from JSON. @param json Source object with both direction fields. */
    void FromJson(nlohmann::json &json) {
        pitch_direction_ = json["pitch_direction"];
        yaw_direction_ = json["yaw_direction"];
    }

    /** @brief Serializes both direction fields. @return Direction-control JSON object. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["pitch_direction"] = pitch_direction_;
        json["yaw_direction"] = yaw_direction_;
        return json;
    }

public:
    int pitch_direction_; ///< Pitch-axis direction command (`-1`, `0`, or `1`).
    int yaw_direction_;   ///< Yaw-axis direction command (`-1`, `0`, or `1`).
};

/**
 * @brief Available implementations of the automatic get-up behavior.
 * @note Supported model: K1 | T1 | T2
 * @note GetUpVersion::kV2 supported model: K1
 */
enum class GetUpVersion {
    kV1 = 0, ///< Initial/base get-up behavior; supported model: K1 | T1 | T2.
    kV2 = 1, ///< BMM get-up behavior; supported model: K1.
};

/**
 * @brief Request payload for automatic get-up.
 * @note Supported model: K1 | T1 | T2
 * @note GetUpVersion::kV2 supported model: K1
 */
class GetUpParameter {
public:
    /** @brief Constructs a request using GetUpVersion::kV1. */
    GetUpParameter() = default;

    /** @brief Constructs a get-up request. @param version Behavior implementation to run. */
    GetUpParameter(GetUpVersion version) :
        version_(version) {
    }

public:
    /**
     * @brief Populates this request from JSON.
     * @param json Source JSON object. Missing `version` defaults to GetUpVersion::kV1.
     */
    void FromJson(nlohmann::json &json) {
        if (json.contains("version")) {
            version_ = static_cast<GetUpVersion>(json["version"]);
        } else {
            version_ = GetUpVersion::kV1;
        }
    }

    /** @brief Serializes the behavior version. @return JSON object containing `version`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["version"] = static_cast<int>(version_);
        return json;
    }

public:
    GetUpVersion version_ = GetUpVersion::kV1; ///< Get-up behavior implementation.
};

/**
 * @brief Request payload for getting up and entering a requested robot mode.
 * @note Supported model: K1 | T1 | T2
 * @note GetUpVersion::kV2 supported model: K1
 * @note T2 supports kV1 with walking mode, but soccer mode is disabled on T2.
 */
class GetUpWithModeParameter {
public:
    /**
     * @brief Constructs an empty request.
     *
     * The mode defaults to RobotMode::kUnknown and the behavior defaults to
     * GetUpVersion::kV1.
     */
    GetUpWithModeParameter() = default;

    /**
     * @brief Constructs a get-up request with a post-action mode.
     * @param mode Mode to enter after getting up, normally walking or soccer.
     * @param version Get-up behavior implementation.
     */
    GetUpWithModeParameter(booster::robot::RobotMode mode, GetUpVersion version = GetUpVersion::kV1) :
        mode_(mode), version_(version) {
    }

public:
    /**
     * @brief Populates this request from JSON.
     * @param json Object containing `mode`; missing `version` defaults to kV1.
     */
    void FromJson(nlohmann::json &json) {
        mode_ = static_cast<booster::robot::RobotMode>(json["mode"]);
        if (json.contains("version")) {
            version_ = static_cast<GetUpVersion>(json["version"]);
        } else {
            version_ = GetUpVersion::kV1;
        }
    }
    /** @brief Serializes the target mode and behavior version. @return Request JSON object. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["mode"] = static_cast<int>(mode_);
        json["version"] = static_cast<int>(version_);
        return json;
    }

public:
    booster::robot::RobotMode mode_ = booster::robot::RobotMode::kUnknown; ///< Mode entered after get-up.
    GetUpVersion version_ = GetUpVersion::kV1; ///< Get-up behavior implementation.
};

/**
 * @brief Request payload for starting or stopping the hand-waving action.
 * @note Supported model: K1 | T1 | T2
 * @note Start and stop supported model: K1 | T1
 * @note T2 supports start only; a manual stop request is refused because its
 * built-in trajectory completes automatically.
 */
class WaveHandParameter {
public:
    /** @brief Constructs an empty payload; members are not initialized. */
    WaveHandParameter() = default;

    /**
     * @brief Constructs a hand-waving request.
     * @param hand_index Hand that performs the action.
     * @param hand_action Action command, normally open to start or close to stop.
     */
    WaveHandParameter(HandIndex hand_index, HandAction hand_action) :
        hand_index_(hand_index), hand_action_(hand_action) {
    }

public:
    /** @brief Populates this request from JSON. @param json Object containing `hand_index` and `hand_action`. */
    void FromJson(nlohmann::json &json) {
        hand_index_ = static_cast<HandIndex>(json["hand_index"]);
        hand_action_ = static_cast<HandAction>(json["hand_action"]);
    }

    /** @brief Serializes this request. @return JSON object containing the hand and action values. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["hand_index"] = static_cast<int>(hand_index_);
        json["hand_action"] = static_cast<int>(hand_action_);
        return json;
    }

public:
    HandIndex hand_index_;   ///< Hand that performs the wave.
    HandAction hand_action_; ///< Command that starts or stops the action.
};

/**
 * @brief Request payload for starting or stopping the handshake action.
 * @note The robot-state-manager handler has no model-name gate. A factory
 * configuration with this action capability disabled, including the current
 * T1_7DofArm configuration, returns kRpcStatusCodeServerRefused. An unavailable
 * action transition returns kRpcStatusCodeStateTransitionFailed.
 * @see @ref b1_loco_model_support_matrix
 */
class HandshakeParameter {
public:
    /** @brief Constructs an empty payload; hand_action_ is not initialized. */
    HandshakeParameter() = default;

    /** @brief Constructs a handshake request. @param hand_action Command that starts or stops the action. */
    HandshakeParameter(HandAction hand_action) :
        hand_action_(hand_action) {
    }

public:
    /** @brief Populates this request from JSON field `hand_action`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        hand_action_ = static_cast<HandAction>(json["hand_action"]);
    }

    /** @brief Serializes the handshake command. @return JSON object containing `hand_action`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["hand_action"] = static_cast<int>(hand_action_);
        return json;
    }

public:
    HandAction hand_action_; ///< Command that starts or stops the handshake action.
};

/**
 * @brief Request payload for the hand-on-chest greeting pose.
 * @note Supported model: T2
 * @note Lowering the hand requires the raised greeting trajectory to be active.
 */
class HandOnChestGreetingParameter {
public:
    /** @brief Constructs a request that leaves the hand lowered. */
    HandOnChestGreetingParameter() = default;

    /** @brief Constructs a greeting request. @param up `true` to raise the hand; `false` to lower it. */
    HandOnChestGreetingParameter(bool up) :
        up_(up) {
    }

public:
    /** @brief Populates this request from JSON field `up`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        up_ = json["up"];
    }

    /** @brief Serializes the greeting command. @return JSON object containing `up`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["up"] = up_;
        return json;
    }

public:
    bool up_ = false; ///< Whether the hand should be raised to the chest.
};

/**
 * @brief Request payload for moving one hand end effector.
 *
 * Target and auxiliary postures are expressed in the robot base/torso frame.
 * The auxiliary posture, when present, defines a point on an arc trajectory.
 * The `new_version` flag selects the corrected orientation semantics used by
 * B1LocoClient::MoveHandEndEffectorV2().
 *
 * @note Supported model: K1 | T1
 */
class MoveHandEndEffectorParameter {
public:
    /** @brief Constructs an empty request with a 1000 ms default duration. */
    MoveHandEndEffectorParameter() = default;

    /**
     * @brief Constructs a request without an auxiliary posture.
     * @param target_posture Target position and orientation in the base frame.
     * @param time_millis Requested motion duration in milliseconds.
     * @param hand_index Hand end effector to move.
     * @deprecated This constructor selects the legacy orientation behavior.
     * Use the overload with `new_version` set to `true` for new integrations.
     */
    MoveHandEndEffectorParameter(
        const Posture &target_posture,
        int time_millis,
        HandIndex hand_index) :
        target_posture_(target_posture),
        time_millis_(time_millis),
        hand_index_(hand_index) {
        has_aux_ = false;
    }
    /**
     * @brief Constructs a request with an auxiliary trajectory posture.
     * @param target_posture Target position and orientation in the base frame.
     * @param aux_posture Auxiliary posture on the end-effector motion arc.
     * @param time_millis Requested motion duration in milliseconds.
     * @param hand_index Hand end effector to move.
     */
    MoveHandEndEffectorParameter(
        const Posture &target_posture,
        const Posture &aux_posture,
        int time_millis,
        HandIndex hand_index) :
        target_posture_(target_posture),
        aux_posture_(aux_posture),
        time_millis_(time_millis),
        hand_index_(hand_index) {
        has_aux_ = true;
    }
    /**
     * @brief Constructs a request and explicitly selects orientation semantics.
     * @param target_posture Target position and orientation in the base frame.
     * @param time_millis Requested motion duration in milliseconds.
     * @param hand_index Hand end effector to move.
     * @param new_version `true` for corrected V2 orientation semantics;
     * `false` for legacy behavior.
     */
    MoveHandEndEffectorParameter(
        const Posture &target_posture,
        int time_millis,
        HandIndex hand_index,
        bool new_version) :
        target_posture_(target_posture),
        time_millis_(time_millis),
        hand_index_(hand_index),
        new_version_(new_version) {
        has_aux_ = false;
    }

public:
    /**
     * @brief Populates this request from JSON.
     * @param json Object containing `target_posture`, `time_millis`,
     * `hand_index`, `has_aux`, and `new_version`. `aux_posture` is required
     * when `has_aux` is `true`.
     */
    void FromJson(nlohmann::json &json) {
        target_posture_.FromJson(json["target_posture"]);
        has_aux_ = json["has_aux"];
        if (has_aux_) {
            aux_posture_.FromJson(json["aux_posture"]);
        }
        time_millis_ = json["time_millis"];
        hand_index_ = static_cast<HandIndex>(json["hand_index"]);
        new_version_ = json["new_version"];
    }

    /**
     * @brief Serializes this end-effector motion request.
     * @return JSON object containing the target and optional auxiliary posture.
     */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["target_posture"] = target_posture_.ToJson();
        if (has_aux_) {
            json["aux_posture"] = aux_posture_.ToJson();
        }
        json["time_millis"] = time_millis_;
        json["hand_index"] = static_cast<int>(hand_index_);
        json["has_aux"] = has_aux_;
        json["new_version"] = new_version_;
        return json;
    }

public:
    Posture target_posture_;    ///< Target posture in the base/torso frame.
    Posture aux_posture_;       ///< Optional posture on the motion arc.
    int time_millis_ = 1000;    ///< Requested motion duration in milliseconds.
    HandIndex hand_index_;      ///< Hand end effector to move.
    bool has_aux_ = false;      ///< Whether aux_posture_ is included in the request.
    bool new_version_ = false;  ///< Whether corrected V2 orientation semantics are used.
};

/** @brief Control laws supported by compatible grippers. */
enum class GripperControlMode {
    kPosition = 0, ///< Position control. Motion stops at the target position or
                   ///< when the configured reaction-force threshold is reached.
    kForce = 1     ///< Force control. If the target position is not reached, the
                   ///< gripper keeps applying the configured force.
};

/**
 * @brief Scaled position, force, and speed parameters for a gripper.
 *
 * Values are device-specific scaling factors rather than portable SI units.
 * Convert them according to the specifications of the installed gripper.
 *
 * For the Inspire EG2-4C2 gripper:
 * - Position `0..1000` maps to an opening of approximately `0..77 mm`.
 * - Force `0..1000` maps to approximately `0..2 kg`.
 * - Speed `0..1000` is dimensionless; the vendor specifies no absolute unit.
 *
 * The commonly accepted command ranges are position `0..1000`, force
 * `50..1000`, and speed `1..1000`.
 */
class GripperMotionParameter {
public:
    /** @brief Constructs a motion parameter with all values set to zero. */
    GripperMotionParameter() = default;

    /**
     * @brief Constructs a gripper motion parameter.
     * @param position Scaled target opening.
     * @param force Scaled force or reaction-force threshold.
     * @param speed Scaled opening/closing speed.
     */
    GripperMotionParameter(const int32_t position, const int32_t force, const int32_t speed) :
        position_(position), force_(force), speed_(speed) {
    }

    /** @brief Populates this parameter from JSON. @param json Object containing all three scale values. */
    void FromJson(nlohmann::json &json) {
        position_ = json["position"];
        force_ = json["force"];
        speed_ = json["speed"];
    }

    /** @brief Serializes the scale values. @return JSON object with `position`, `force`, and `speed`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["position"] = position_;
        json["force"] = force_;
        json["speed"] = speed_;
        return json;
    }

public:
    int32_t position_ = 0; ///< Scaled target opening; commonly `0..1000`.
    int32_t force_ = 0;    ///< Scaled force value or threshold; commonly `50..1000`.
    int32_t speed_ = 0;    ///< Scaled motion speed; commonly `1..1000`.
};

/**
 * @brief Request payload for controlling a gripper on either hand.
 * @note Supported model: K1 | T1 | T2
 * @note Requires a compatible installed gripper reported by
 * B1LocoClient::GetHands(). The request is refused while the robot is in
 * damping mode.
 */
class ControlGripperParameter {
public:
    /** @brief Constructs an empty payload; enum members are not initialized. */
    ControlGripperParameter() = default;

    /**
     * @brief Constructs a gripper-control request.
     * @param motion_param Target position, force, and speed scales.
     * @param mode Gripper control law.
     * @param hand_index Hand whose gripper is controlled.
     */
    ControlGripperParameter(const GripperMotionParameter &motion_param, GripperControlMode mode, HandIndex hand_index) :
        motion_param_(motion_param), mode_(mode), hand_index_(hand_index) {
    }

public:
    /** @brief Populates this request from JSON. @param json Source object with motion, mode, and hand fields. */
    void FromJson(nlohmann::json &json) {
        motion_param_.FromJson(json["motion_param"]);
        mode_ = static_cast<GripperControlMode>(json["mode"]);
        hand_index_ = static_cast<HandIndex>(json["hand_index"]);
    }

    /** @brief Serializes this gripper request. @return Gripper-control JSON object. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["motion_param"] = motion_param_.ToJson();
        json["mode"] = static_cast<int>(mode_);
        json["hand_index"] = static_cast<int>(hand_index_);
        return json;
    }

public:
    GripperMotionParameter motion_param_; ///< Target gripper motion parameters.
    GripperControlMode mode_;             ///< Selected gripper control law.
    HandIndex hand_index_;                ///< Hand whose gripper is controlled.
};

/**
 * @brief Request payload for moving both hand end effectors synchronously.
 * @note Supported model: K1 | T1
 */
class MoveDualHandEndEffectorParameter {
public:
    /** @brief Constructs an empty request with a 1000 ms default duration. */
    MoveDualHandEndEffectorParameter() = default;

    /**
     * @brief Constructs a synchronized dual-hand request.
     * @param left_target_posture Left-hand target in the base/torso frame.
     * @param right_target_posture Right-hand target in the base/torso frame.
     * @param time_millis Requested motion duration in milliseconds.
     */
    MoveDualHandEndEffectorParameter(
        const Posture &left_target_posture,
        const Posture &right_target_posture,
        int time_millis) :
        left_target_posture_(left_target_posture),
        right_target_posture_(right_target_posture),
        time_millis_(time_millis) {
    }

public:
    /** @brief Populates this request from JSON. @param json Object containing both postures and `time_millis`. */
    void FromJson(nlohmann::json &json) {
        left_target_posture_.FromJson(json["left_target_posture"]);
        right_target_posture_.FromJson(json["right_target_posture"]);
        time_millis_ = json["time_millis"];
    }

    /** @brief Serializes the synchronized request. @return JSON object containing both targets and duration. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["left_target_posture"] = left_target_posture_.ToJson();
        json["right_target_posture"] = right_target_posture_.ToJson();
        json["time_millis"] = time_millis_;
        return json;
    }

public:
    Posture left_target_posture_;  ///< Left-hand target in the base/torso frame.
    Posture right_target_posture_; ///< Right-hand target in the base/torso frame.
    int time_millis_ = 1000;       ///< Requested synchronized motion duration.
};

/** @brief Request payload for querying a transform between two robot frames. */
class GetFrameTransformParameter {
public:
    /** @brief Constructs an empty payload; frame members are not initialized. */
    GetFrameTransformParameter() = default;

    /** @brief Constructs a frame-transform query. @param src Source frame. @param dst Destination frame. */
    GetFrameTransformParameter(const Frame &src, const Frame &dst) :
        src_(src), dst_(dst) {
    }

public:
    /** @brief Populates this query from JSON. @param json Object containing `src` and `dst`. */
    void FromJson(nlohmann::json &json) {
        src_ = static_cast<Frame>(json["src"]);
        dst_ = static_cast<Frame>(json["dst"]);
    }

    /** @brief Serializes this query. @return JSON object containing source and destination frames. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["src"] = static_cast<int>(src_);
        json["dst"] = static_cast<int>(dst_);
        return json;
    }

public:
    Frame src_; ///< Source coordinate frame.
    Frame dst_; ///< Destination coordinate frame.
};

/**
 * @brief Legacy-backend request payload for hand end-effector control mode.
 * @deprecated The robot-state-manager RPC handler does not implement this ID
 * and returns kRpcStatusCodeBadRequest. The legacy LocoApiService handler does
 * implement it on the same locomotion topic. New integrations should not rely
 * on the operation unless the active server backend is known.
 */
class SwitchHandEndEffectorControlModeParameter {
public:
    /** @brief Constructs an empty payload; switch_on_ is not initialized. */
    SwitchHandEndEffectorControlModeParameter() = default;

    /** @brief Constructs a mode-switch request. @param switch_on `true` to enable end-effector control. */
    SwitchHandEndEffectorControlModeParameter(bool switch_on) :
        switch_on_(switch_on) {
    }

public:
    /** @brief Populates this request from JSON field `switch_on`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        switch_on_ = json["switch_on"];
    }

    /** @brief Serializes the requested state. @return JSON object containing `switch_on`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["switch_on"] = switch_on_;
        return json;
    }

public:
    bool switch_on_; ///< Whether hand end-effector control should be enabled.
};

/**
 * @brief Scaled command parameters for one dexterous-hand degree of freedom.
 *
 * The values are device-specific scaling factors. Convert them according to
 * the installed hand's specification.
 *
 * For the Inspire RH56 Dexterous Hand:
 * - `seq` `0..5`: little, ring, middle, index, thumb bend, thumb rotation.
 * - `angle` `0..1000`: normally closed to open. Approximate RH56 physical
 *   ranges are 90 to 165 degrees for thumb rotation, -130 to 53.6 degrees for
 *   thumb bend, and 19 to 176.7 degrees for the other fingers.
 * - `force`: `0..1500` for thumb axes (approximately 0 to 1.5 kg) and
 *   `0..1000` for other fingers (approximately 0 to 1 kg).
 * - `speed` `0..1000`: dimensionless vendor scale.
 */
class DexterousFingerParameter {
public:
    /** @brief Constructs an invalid/unselected finger command with zeroed scales. */
    DexterousFingerParameter() = default;

    /**
     * @brief Constructs a dexterous-finger command.
     * @param seq Finger/axis sequence number.
     * @param angle Scaled target angle.
     * @param force Scaled target force.
     * @param speed Scaled motion speed.
     */
    DexterousFingerParameter(const int32_t seq, const int32_t angle,
                             const int32_t force, const int32_t speed) :
        seq_(seq),
        angle_(angle),
        force_(force), speed_(speed) {
    }

    /** @brief Populates this command from JSON. @param json Object containing `seq`, `angle`, `force`, and `speed`. */
    void FromJson(nlohmann::json &json) {
        seq_ = json["seq"];
        angle_ = json["angle"];
        force_ = json["force"];
        speed_ = json["speed"];
    }

    /** @brief Serializes this finger command. @return JSON object containing all scale values. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["seq"] = seq_;
        json["angle"] = angle_;
        json["force"] = force_;
        json["speed"] = speed_;
        return json;
    }

public:
    int32_t seq_ = -1;  ///< Finger/axis sequence number; `-1` means unselected.
    int32_t angle_ = 0; ///< Scaled target angle.
    int32_t force_ = 0; ///< Scaled target force.
    int32_t speed_ = 0; ///< Scaled motion speed.
};

/**
 * @brief Request payload for controlling a dexterous hand.
 *
 * The request contains one command per controlled finger/axis, the target hand,
 * and the installed hand model.
 *
 * @note Supported model: K1 | T1 | T2
 * @note Requires a compatible installed dexterous hand reported by
 * B1LocoClient::GetHands(). The request is refused while the robot is in
 * damping mode.
 */
class ControlDexterousHandParameter {
public:
    /** @brief Constructs an empty payload; enum members are not initialized. */
    ControlDexterousHandParameter() = default;

    /**
     * @brief Constructs a dexterous-hand request.
     * @param finger_params Commands for the finger/axes to control.
     * @param hand_index Target hand.
     * @param hand_type Installed dexterous-hand model.
     */
    ControlDexterousHandParameter(
        const std::vector<DexterousFingerParameter> &finger_params, HandIndex hand_index, BoosterHandType hand_type = BoosterHandType::kInspireHand) :
        finger_params_(finger_params),
        hand_index_(hand_index),
        hand_type_(hand_type) {
    }

    /**
     * @brief Populates this request from JSON.
     * @param json Object containing `finger_params`, `hand_index`, and `hand_type`.
     * @note Parsed finger commands are appended to finger_params_; clear the
     * vector before calling when reusing an existing object.
     */
    void FromJson(nlohmann::json &json) {
        for (auto &finger_param : json["finger_params"]) {
            DexterousFingerParameter param;
            param.FromJson(finger_param);
            finger_params_.push_back(param);
        }
        hand_index_ = static_cast<HandIndex>(json["hand_index"]);
        hand_type_ = static_cast<BoosterHandType>(json["hand_type"]);
    }

    /** @brief Serializes this hand request. @return JSON object containing finger commands and hand metadata. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        for (auto &finger_param : finger_params_) {
            json["finger_params"].push_back(finger_param.ToJson());
        }
        json["hand_index"] = static_cast<int>(hand_index_);
        json["hand_type"] = static_cast<int>(hand_type_);
        return json;
    }

public:
    std::vector<DexterousFingerParameter> finger_params_; ///< Commands for individual finger/axes.
    HandIndex hand_index_;                                ///< Target left or right hand.
    BoosterHandType hand_type_;                           ///< Installed dexterous-hand model.
};

/**
 * @brief Identifiers for built-in upper-body dances and gestures.
 * @note Supported model: K1 | T1
 */
enum class DanceId {
    kNewYear = 0,          ///< New Year dance.
    kNezha = 1,            ///< Nezha dance.
    kTowardsFuture = 2,    ///< Towards Future dance.
    kDabbingGesture = 3,   ///< Dabbing gesture.
    kUltramanGesture = 4,  ///< Ultraman gesture.
    kRespectGesture = 5,   ///< Respect gesture.
    kCheeringGesture = 6,  ///< Cheering gesture.
    kLuckyCatGesture = 7,  ///< Lucky-cat gesture.
    kStop = 1000,          ///< Stop the current upper-body dance or gesture.
};

/**
 * @brief Request payload for selecting an upper-body dance or gesture.
 * @note Supported model: K1 | T1
 */
class DanceParameter {
public:
    /** @brief Constructs an empty payload; dance_id_ is not initialized. */
    DanceParameter() = default;

    /** @brief Constructs a dance request. @param dance_id Dance, gesture, or stop command. */
    DanceParameter(DanceId dance_id) :
        dance_id_(dance_id) {
    }

public:
    /** @brief Populates this request from JSON field `dance_id`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        dance_id_ = json["dance_id"];
    }

    /** @brief Serializes the selected dance. @return JSON object containing `dance_id`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["dance_id"] = dance_id_;
        return json;
    }

public:
    DanceId dance_id_; ///< Dance, gesture, or stop command.
};

/** @brief Request payload for playing an audio file on the robot. */
class PlaySoundParameter {
public:
    /** @brief Constructs a request with an empty file path. */
    PlaySoundParameter() = default;

    /** @brief Constructs a sound-playback request. @param sound_file_path Path visible to the robot service. */
    PlaySoundParameter(const std::string &sound_file_path) :
        sound_file_path_(sound_file_path) {
    }

    /** @brief Populates this request from JSON field `sound_file_path`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        sound_file_path_ = json["sound_file_path"];
    }
    /** @brief Serializes the audio file path. @return JSON object containing `sound_file_path`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["sound_file_path"] = sound_file_path_;
        return json;
    }

private:
    std::string sound_file_path_; ///< Audio file path resolved by the robot service.
};

/**
 * @brief Request payload for replaying a recorded trajectory file.
 * @note Supported model: K1 | T1
 */
class ReplayTrajectoryParameter {
public:
    /** @brief Constructs a request with an empty trajectory path. */
    ReplayTrajectoryParameter() = default;

    /** @brief Constructs a replay request. @param traj_file_path Trajectory file path visible to the robot service. */
    ReplayTrajectoryParameter(const std::string &traj_file_path) :
        traj_file_path_(traj_file_path) {
    }

    /** @brief Populates this request from JSON field `traj_file_path`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        traj_file_path_ = json["traj_file_path"];
    }

    /** @brief Serializes the trajectory path. @return JSON object containing `traj_file_path`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["traj_file_path"] = traj_file_path_;
        return json;
    }

private:
    std::string traj_file_path_; ///< Trajectory file path resolved by the robot service.
};

/**
 * @brief Request payload for enabling or disabling zero-torque drag mode.
 * @note Supported model: K1 | T1
 */
class ZeroTorqueDragParameter {
public:
    /** @brief Constructs a request with drag mode disabled. */
    ZeroTorqueDragParameter() = default;

    /** @brief Constructs a zero-torque drag request. @param enable `true` to enable drag mode. */
    ZeroTorqueDragParameter(bool enable) :
        enable_(enable) {
    }

    /** @brief Populates this request from JSON field `enable`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        enable_ = json["enable"];
    }

    /** @brief Serializes the requested state. @return JSON object containing `enable`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["enable"] = enable_;
        return json;
    }

private:
    bool enable_ = false; ///< Whether zero-torque drag mode should be enabled.
};

/**
 * @brief Request payload for starting or stopping trajectory recording.
 * @note Supported model: K1 | T1
 */
class RecordTrajectoryParameter {
public:
    /** @brief Constructs a request with recording disabled. */
    RecordTrajectoryParameter() = default;

    /** @brief Constructs a recording request. @param enable `true` to start; `false` to stop. */
    RecordTrajectoryParameter(bool enable) :
        enable_(enable) {
    }

    /** @brief Populates this request from JSON field `enable`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        enable_ = json["enable"];
    }

    /** @brief Serializes the requested recording state. @return JSON object containing `enable`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["enable"] = enable_;
        return json;
    }

private:
    bool enable_ = false; ///< Whether trajectory recording should be active.
};

/**
 * @brief Identifiers for built-in whole-body dance trajectories.
 *
 * @note Supported model: K1 | T2
 * @note Values 0 through 9 supported model: K1
 * @note kBowAndArrow and kCharlestonDance supported model: T2
 */
enum class WholeBodyDanceId {
    kArbicDance = 0,          ///< Arabic dance trajectory; supported model: K1.
    kMichaelDance1 = 1,       ///< Michael dance, part 1; supported model: K1.
    kMichaelDance2 = 2,       ///< Michael dance, part 2; supported model: K1.
    kMichaelDance3 = 3,       ///< Michael dance, part 3; supported model: K1.
    kBoxingStyleKick = 5,     ///< Boxing-style kick trajectory; supported model: K1.
    kRoundhouseKick = 6,      ///< Roundhouse-kick trajectory; supported model: K1.
    kShanHeGuRenDance = 7,    ///< Shan He Gu Ren dance trajectory; supported model: K1.
    kGaiGeChunFengDance = 8,  ///< Gai Ge Chun Feng dance trajectory; supported model: K1.
    kMichaelDance1And2 = 9,   ///< Combined Michael dance parts 1 and 2; supported model: K1.
    kBowAndArrow = 10,        ///< Bow-and-arrow trajectory; supported model: T2.
    kCharlestonDance = 11,    ///< Charleston dance trajectory; supported model: T2.
};

/**
 * @brief Request payload for selecting a whole-body dance trajectory.
 * @note Supported model: K1 | T2
 * @note Availability is determined by the selected WholeBodyDanceId value.
 */
class WholeBodyDanceParameter {
public:
    /** @brief Constructs an empty payload; dance_id_ is not initialized. */
    WholeBodyDanceParameter() = default;

    /** @brief Constructs a whole-body dance request. @param dance_id Trajectory to execute. */
    WholeBodyDanceParameter(WholeBodyDanceId dance_id) :
        dance_id_(dance_id) {
    }

public:
    /** @brief Populates this request from JSON field `dance_id`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        dance_id_ = json["dance_id"];
    }

    /** @brief Serializes the selected trajectory. @return JSON object containing `dance_id`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["dance_id"] = dance_id_;
        return json;
    }

public:
    WholeBodyDanceId dance_id_; ///< Whole-body trajectory to execute.
};

/** @brief Request payload for starting or stopping upper-body custom control. */
class UpperBodyCustomControlParameter {
public:
    /** @brief Constructs an empty payload; start_ is not initialized. */
    UpperBodyCustomControlParameter() = default;

    /** @brief Constructs an upper-body control request. @param start `true` to start; `false` to stop. */
    UpperBodyCustomControlParameter(bool start) :
        start_(start) {
    }

    /** @brief Populates this request from JSON field `start`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        start_ = json["start"];
    }

    /** @brief Serializes the requested state. @return JSON object containing `start`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["start"] = start_;
        return json;
    }

public:
    bool start_; ///< Whether upper-body custom control should be active.
};

/** @brief Joint-index conventions supported by custom trained models. */
enum class JointOrder {
    kMuJoCo = 0,  ///< Joint order used by MuJoCo training environments.
    kIsaacLab = 1, ///< Joint order used by Isaac Lab training environments.
};

/**
 * @brief Per-model control gains and action scales for a trained trajectory.
 *
 * Each vector is ordered according to CustomModel::joint_order_. Multiple
 * entries may be supplied in CustomModel::params_ when the model requires more
 * than one parameter set.
 */
class CustomModelParams {
public:
    /** @brief Constructs an empty parameter set. */
    CustomModelParams() = default;

    /**
     * @brief Constructs a trained-model parameter set.
     * @param action_scale Per-joint action scaling factors.
     * @param kp Per-joint proportional gains.
     * @param kd Per-joint derivative gains.
     */
    CustomModelParams(const std::vector<double> &action_scale,
                      const std::vector<double> &kp,
                      const std::vector<double> &kd) :
        action_scale_(action_scale),
        kp_(kp), kd_(kd) {
    }

    /**
     * @brief Populates fields present in a JSON object.
     * @param json Source object. Missing arrays leave the corresponding member unchanged.
     */
    void FromJson(nlohmann::json &json) {
        if (json.contains("action_scale")) {
            action_scale_ = json["action_scale"].get<std::vector<double>>();
        }
        if (json.contains("kp")) {
            kp_ = json["kp"].get<std::vector<double>>();
        }
        if (json.contains("kd")) {
            kd_ = json["kd"].get<std::vector<double>>();
        }
    }

    /** @brief Serializes all model parameters. @return JSON object containing `action_scale`, `kp`, and `kd`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["action_scale"] = action_scale_;
        json["kp"] = kp_;
        json["kd"] = kd_;
        return json;
    }

public:
    std::vector<double> action_scale_; ///< Per-joint action scaling factors.
    std::vector<double> kp_;           ///< Per-joint proportional gains.
    std::vector<double> kd_;           ///< Per-joint derivative gains.
};

/** @brief Model file and runtime parameters used by a custom trained trajectory. */
class CustomModel {
public:
    /** @brief Constructs an empty model using MuJoCo joint order. */
    CustomModel() = default;

    /**
     * @brief Constructs a custom model description.
     * @param file_path Model file path visible to the robot service.
     * @param params One or more control parameter sets.
     * @param joint_order Joint-index convention used by the model and vectors.
     */
    CustomModel(const std::string &file_path,
                const std::vector<CustomModelParams> &params,
                JointOrder joint_order) :
        file_path_(file_path),
        params_(params),
        joint_order_(joint_order) {
    }

    /**
     * @brief Populates this model from JSON.
     * @param json Object containing `file_path`, optional array `params`, and `joint_order`.
     */
    void FromJson(nlohmann::json &json) {
        file_path_ = json["file_path"];
        params_.clear();
        if (json.contains("params") && json["params"].is_array()) {
            for (auto &item : json["params"]) {
                CustomModelParams p;
                p.FromJson(item);
                params_.push_back(p);
            }
        }
        joint_order_ = static_cast<JointOrder>(json["joint_order"]);
    }

    /** @brief Serializes this model description. @return JSON object containing file, parameters, and joint order. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["file_path"] = file_path_;
        json["params"] = nlohmann::json::array();
        for (const auto &p : params_) {
            json["params"].push_back(p.ToJson());
        }
        json["joint_order"] = static_cast<int>(joint_order_);
        return json;
    }

public:
    std::string file_path_;                 ///< Model file path resolved by the robot service.
    std::vector<CustomModelParams> params_; ///< Runtime control parameter sets.
    JointOrder joint_order_ = JointOrder::kMuJoCo; ///< Joint-index convention.
};

/**
 * @brief Complete load request for a custom trained trajectory and its model.
 * @note Supported model: K1 | T2
 */
class CustomTrainedTraj {
public:
    /** @brief Constructs an empty trajectory request. */
    CustomTrainedTraj() = default;

    /**
     * @brief Constructs a custom trained-trajectory request.
     * @param traj_file_path Trajectory file path visible to the robot service.
     * @param model Model and control configuration used to replay the trajectory.
     */
    CustomTrainedTraj(const std::string &traj_file_path, const CustomModel &model) :
        traj_file_path_(traj_file_path),
        model_(model) {
    }

    /** @brief Populates this request from JSON. @param json Object containing `traj_file_path` and `model`. */
    void FromJson(nlohmann::json &json) {
        traj_file_path_ = json["traj_file_path"];
        model_.FromJson(json["model"]);
    }

    /** @brief Serializes the trajectory and model. @return Complete load-request JSON object. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["traj_file_path"] = traj_file_path_;
        json["model"] = model_.ToJson();
        return json;
    }

public:
    std::string traj_file_path_; ///< Trajectory file path resolved by the robot service.
    CustomModel model_;          ///< Model and runtime control configuration.
};

/**
 * @brief Response returned after loading a custom trained trajectory.
 * @note Supported model: K1 | T2
 */
class LoadCustomTrainedTrajResponse {
public:
    /** @brief Constructs an empty response. */
    LoadCustomTrainedTrajResponse() = default;

    /** @brief Populates this response from JSON field `tid`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        tid_ = json["tid"];
    }

    /** @brief Serializes the trajectory identifier. @return JSON object containing `tid`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["tid"] = tid_;
        return json;
    }

public:
    std::string tid_; ///< Service-assigned trajectory identifier, normally a UUID.
};

/**
 * @brief Request payload that addresses a previously loaded trained trajectory.
 * @note Supported model: K1 | T2
 */
class CustomTrainedTrajParameter {
public:
    /** @brief Constructs a request with an empty trajectory identifier. */
    CustomTrainedTrajParameter() = default;

    /** @brief Constructs a trajectory-addressing request. @param tid Identifier returned by the load operation. */
    CustomTrainedTrajParameter(const std::string &tid) :
        tid_(tid) {
    }

    /** @brief Populates this request from JSON field `tid`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        tid_ = json["tid"];
    }

    /** @brief Serializes the trajectory identifier. @return JSON object containing `tid`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["tid"] = tid_;
        return json;
    }

public:
    std::string tid_; ///< Identifier of a loaded custom trained trajectory.
};

/**
 * @brief Response describing trained-trajectory execution state.
 *
 * For a custom trajectory, traj_id_ is the UUID returned by the load operation.
 * For a built-in trajectory, it is a stable public action or dance identifier.
 */
class GetTrainedTrajStatusResponse {
public:
    /** @brief Constructs an idle response with an empty trajectory identifier. */
    GetTrainedTrajStatusResponse() = default;

    /**
     * @brief Populates this response from JSON.
     * @param json Object containing `status`; missing `traj_id` becomes an empty string.
     */
    void FromJson(nlohmann::json &json) {
        status_ = static_cast<booster::robot::TrainedTrajStatus>(json["status"]);
        traj_id_ = json.value("traj_id", "");
    }

    /** @brief Serializes the execution state. @return JSON object containing `status` and `traj_id`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["status"] = static_cast<int>(status_);
        json["traj_id"] = traj_id_;
        return json;
    }

public:
    booster::robot::TrainedTrajStatus status_ =
        booster::robot::TrainedTrajStatus::kIdle; ///< Current trained-trajectory state.
    std::string traj_id_; ///< Active trajectory ID, or empty when no trajectory is identified.
};

/**
 * @brief Requested implementations of the visual side-foot kick.
 * @note The server does not reject either value by robot model. kV1 requests
 * the base visual-kick path. kV2 uses the WBC path when enabled by the factory
 * software and otherwise falls back to the configured non-WBC path.
 * Missing or unreachable motions return kRpcStatusCodeStateTransitionFailed.
 * @see @ref b1_loco_model_support_matrix
 */
enum class VisualKickVersion {
    kV1 = 0, ///< Requests the base visual-kick path.
    kV2 = 1, ///< Uses WBC toggle tasks or the configured non-WBC fallback path.
};

/**
 * @brief Request payload for starting or stopping the visual side-foot kick.
 * @note Runtime behavior is determined by the factory gait capability and the
 * motions registered in the robot software, not by a model-name gate. Detect
 * an unavailable path through kRpcStatusCodeStateTransitionFailed.
 * @see @ref b1_loco_model_support_matrix
 */
class VisualKickParameter {
public:
    /** @brief Constructs an empty payload; members are not initialized. */
    VisualKickParameter() = default;

    /**
     * @brief Constructs a visual-kick request.
     * @param start `true` to start the action; `false` to stop it.
     * @param version Visual-kick behavior implementation.
     */
    VisualKickParameter(bool start, VisualKickVersion version = VisualKickVersion::kV1) :
        start_(start), version_(version) {
    }

public:
    /** @brief Populates this request from JSON fields `start` and `version`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        start_ = json["start"];
        version_ = static_cast<VisualKickVersion>(json["version"]);
    }

    /** @brief Serializes the action state and version. @return Visual-kick request JSON object. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["start"] = start_;
        json["version"] = static_cast<int>(version_);
        return json;
    }

private:
    bool start_;                ///< Whether the visual-kick action should run.
    VisualKickVersion version_; ///< Visual-kick behavior implementation.
};

/**
 * @brief Request payload for entering or leaving the lion-dance preparation pose.
 *
 * The preparation pose is entered from walking mode and is the safe transition
 * point for LionDanceMoveParameter and LionDanceStartParameter operations.
 *
 * @note Supported model: K1
 */
class LionDancePrepareParameter {
public:
    /** @brief Constructs an empty payload; start_ is not initialized. */
    LionDancePrepareParameter() = default;

    /** @brief Constructs a preparation request. @param start `true` to enter; `false` to leave the pose. */
    LionDancePrepareParameter(bool start) :
        start_(start) {
    }

    /** @brief Populates this request from JSON field `start`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        start_ = json["start"];
    }
    /** @brief Serializes the requested state. @return JSON object containing `start`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["start"] = start_;
        return json;
    }

private:
    bool start_; ///< Whether the robot should enter the preparation pose.
};

/**
 * @brief Request payload for starting or stopping lion-dance locomotion.
 *
 * Enter this behavior only from the lion-dance preparation pose or walking
 * gait. It may transition to a lion-dance routine.
 *
 * @note Supported model: K1
 */
class LionDanceMoveParameter {
public:
    /** @brief Constructs an empty payload; start_ is not initialized. */
    LionDanceMoveParameter() = default;

    /** @brief Constructs a locomotion request. @param start `true` to start; `false` to stop. */
    LionDanceMoveParameter(bool start) :
        start_(start) {
    }
    /** @brief Populates this request from JSON field `start`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        start_ = json["start"];
    }
    /** @brief Serializes the requested state. @return JSON object containing `start`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["start"] = start_;
        return json;
    }

private:
    bool start_; ///< Whether lion-dance locomotion should be active.
};

/**
 * @brief Request payload for starting a specific lion-dance routine.
 *
 * @warning Start a routine only from the lion-dance preparation or movement
 * state. Entering from another state can create discontinuous arm commands and
 * presents a safety and hardware-damage risk.
 * @note Supported model: K1
 */
class LionDanceStartParameter {
public:
    /** @brief Constructs an empty payload; dance_idx_ is not initialized. */
    LionDanceStartParameter() = default;

    /** @brief Constructs a lion-dance request. @param dance_idx Service-defined lion-dance routine index. */
    LionDanceStartParameter(int dance_idx) :
        dance_idx_(dance_idx) {
    }

    /** @brief Populates this request from JSON field `dance_idx`. @param json Source JSON object. */
    void FromJson(nlohmann::json &json) {
        dance_idx_ = json["dance_idx"];
    }
    /** @brief Serializes the routine index. @return JSON object containing `dance_idx`. */
    nlohmann::json ToJson() const {
        nlohmann::json json;
        json["dance_idx"] = dance_idx_;
        return json;
    }

private:
    int dance_idx_; ///< Service-defined lion-dance routine index.
};

}
}
} // namespace booster::robot::b1

#endif // __BOOSTER_ROBOTICS_SDK_B1_LOCO_API_HPP__
