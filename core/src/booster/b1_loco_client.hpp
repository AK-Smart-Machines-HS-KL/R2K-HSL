#ifndef __BOOSTER_ROBOTICS_SDK_B1_LOCO_CLIENT_HPP__
#define __BOOSTER_ROBOTICS_SDK_B1_LOCO_CLIENT_HPP__

#include <memory>

#include <booster/robot/rpc/rpc_client.hpp>
#include "b1_loco_api.hpp"

namespace booster {
namespace robot {
namespace b1 {

/**
 * @file b1_loco_client.hpp
 * @brief Synchronous and fire-and-forget client APIs for B1 locomotion.
 */

/**
 * @brief Client for the robot locomotion RPC service.
 *
 * Call Init() before any request method. Most operations wait for a service
 * response and return an RPC status code; MoveCommand() is the main
 * fire-and-forget convenience method. Query methods parse JSON response bodies
 * into the supplied output objects and may throw nlohmann::json::exception if
 * a successful response contains malformed data.
 *
 * @note Supported model: K1 | T1 | T2
 * @note Model restrictions are repeated on the affected methods and summarized
 * by LocoApiId in b1_loco_api.hpp.
 *
 * @note This class does not initialize ChannelFactory. Applications must
 * initialize the channel transport before calling Init().
 * @see LocoApiId
 * @see kRpcStatusCodeSuccess
 */
class B1LocoClient {
public:
    /** @brief Constructs an uninitialized locomotion client. */
    B1LocoClient() = default;

    /** @brief Destroys the client and its RPC transport handle. */
    ~B1LocoClient() = default;

    /**
     * @brief Initializes the client for the default robot.
     *
     * The RPC channel is `rt/LocoApiTopic`.
     */
    void Init();

    /**
     * @brief Initializes the client for a named robot.
     *
     * @param robot_name Robot-name suffix. An empty string selects the default
     * robot; otherwise the RPC channel is `rt/LocoApiTopic/<robot_name>`.
     */
    void Init(const std::string &robot_name);

    /**
     * @brief Waits for the locomotion RPC service to become available.
     *
     * @param timeout_ms Maximum wait duration in milliseconds.
     * @param require_response_path `true` to require both request and response
     * endpoints; `false` to require only the request endpoint.
     * @return `true` when the requested endpoints are available before the
     * timeout; otherwise `false`. Also returns `false` before Init().
     */
    bool WaitForService(
        int64_t timeout_ms = booster::robot::RpcClient::kDefaultWaitForServiceTimeoutMs,
        bool require_response_path = true);

    /**
     * @brief Sends a request and waits up to the default one-second timeout.
     *
     * @param api_id Operation identifier.
     * @param param Serialized JSON request body, or an empty string for an
     * operation without a payload.
     * @return RPC response status; kRpcStatusCodeSuccess on success.
     * @pre Init() has been called.
     */
    int32_t SendApiRequest(LocoApiId api_id, const std::string &param);

    /**
     * @brief Sends a request and waits for a response with a custom timeout.
     *
     * @param api_id Operation identifier.
     * @param param Serialized JSON request body.
     * @param timeout_ms Response timeout in milliseconds.
     * @return RPC response status; kRpcStatusCodeSuccess on success.
     * @pre Init() has been called.
     */
    int32_t SendApiRequest(LocoApiId api_id, const std::string &param, int64_t timeout_ms);

    /**
     * @brief Sends a request without waiting for service execution to finish.
     *
     * @param api_id Operation identifier.
     * @param param Serialized JSON request body.
     * @return Transport submission status. Success confirms submission, not
     * execution by the robot.
     * @pre Init() has been called.
     */
    int32_t SendApiRequestFireAndForget(LocoApiId api_id, const std::string &param);

    /**
     * @brief Sends a request and returns the complete RPC response.
     *
     * @param api_id Operation identifier.
     * @param param Serialized JSON request body.
     * @param[out] resp Complete response header and body, including error
     * responses.
     * @return RPC response status; kRpcStatusCodeSuccess on success.
     * @pre Init() has been called.
     */
    int32_t SendApiRequestWithResponse(LocoApiId api_id, const std::string &param, Response &resp);

    /**
     * @brief Change robot mode
     * @note Supported model: K1 | T1 | T2
     * @note RobotMode::kSoccer supported model: K1 | T1
     *
     * @param mode robot mode, see RobotMode enum for available mode definitions
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t ChangeMode(RobotMode mode) {
        ChangeModeParameter change_mode(mode);
        std::string param = change_mode.ToJson().dump();
        return SendApiRequest(LocoApiId::kChangeMode, param);
    }

    /**
     * @brief Get current robot mode
     *
     * @param[out] get_mode_response Reference to store the response data, including:
     * - mode (RobotMode enum value)
     *
     * @return 0 if success, otherwise return error code
     * @see ChangeMode() for mode switching API
     * @see RobotMode enum for available mode definitions
     */
    int32_t GetMode(GetModeResponse &get_mode_response) {
        std::string param{};
        Response resp;
        int32_t ret = SendApiRequestWithResponse(LocoApiId::kGetMode,
                                                 param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        get_mode_response.FromJson(body_json);
        return ret;
    }

    /**
     * @brief Get current robot status
     *
     * @param[out] get_status_response Reference to store the response data, including:
     * - current_mode (RobotMode enum value)
     * - current_body_control (BodyControl enum value)
     * - current_actions (vector of Action enum values)
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t GetStatus(GetStatusResponse &get_status_response) {
        std::string param{};
        Response resp;
        int32_t ret = SendApiRequestWithResponse(LocoApiId::kGetStatus,
                                                 param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        get_status_response.FromJson(body_json);
        return ret;
    }

    /**
     * @brief Get robot info
     *
     * @param[out] get_robot_info_response Reference to store the response data, including:
     * - name (std::string)
     * - nickname (std::string)
     * - version (std::string)
     * - model (std::string)
     * - serial_number (std::string)
     * - edition (std::string)
     * - region (std::string)
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t GetRobotInfo(GetRobotInfoResponse &get_robot_info_response) {
        std::string param{};
        Response resp;
        int32_t ret = SendApiRequestWithResponse(LocoApiId::kGetRobotInfo,
                                                 param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        get_robot_info_response.FromJson(body_json);
        return ret;
    }

    /**
     * @brief Query IMU devices (static catalog from robot_config). RPC JSON uses field "imus".
     * @param[out] info kind_ is kSensors; json_ holds RPC body. Use booster::robot::ImuInfoListFromDeviceInfo(list, info)
     * (see device_info_parser.hpp).
     * @return 0 if success, otherwise error code
     */
    int32_t GetSensors(DeviceInfo &info) {
        std::string param{};
        Response resp;
        int32_t ret =
            SendApiRequestWithResponse(LocoApiId::kGetSensors, param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        info.FromJson(body_json);
        info.kind_ = DeviceInfoKind::kSensors;
        return ret;
    }

    /**
     * @brief Query hand end-effector catalog from robot_config (static). RPC JSON uses field
     * "hands"; use booster::robot::HandListFromDeviceInfo(list, info) (see device_info_parser.hpp).
     *
     * @param[out] info kind_ is kHands; json_ holds RPC body (field "hands").
     * @return 0 if success, otherwise error code
     */
    int32_t GetHands(DeviceInfo &info) {
        std::string param{};
        Response resp;
        int32_t ret =
            SendApiRequestWithResponse(LocoApiId::kGetHands, param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        info.FromJson(body_json);
        info.kind_ = DeviceInfoKind::kHands;
        return ret;
    }

    /**
     * @brief Query static robot model (URDF-derived via RBDL on the motion stack).
     * RPC JSON nests model under "robot_model". Use booster::robot::RobotModelFromDeviceInfo(model, info)
     * (see device_info_parser.hpp).
     *
     * @param[out] info kind_ is kRobotModel; json_ holds RPC body (key "robot_model").
     * @return 0 if success, otherwise error code
     */
    int32_t GetRobotModel(DeviceInfo &info) {
        std::string param{};
        Response resp;
        int32_t ret =
            SendApiRequestWithResponse(LocoApiId::kGetRobotModel, param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        info.FromJson(body_json);
        info.kind_ = DeviceInfoKind::kRobotModel;
        return ret;
    }

    /**
     * @brief Move robot
     *
     * @param vx linear velocity in x direction, unit: m/s
     * @param vy linear velocity in y direction, unit: m/s
     * @param vyaw angular velocity, unit: rad/s
     *
     * @return 0 if success, otherwise return error code
     * @note The service clamps the requested velocity using limits from the
     * active robot mode and model configuration.
     */
    int32_t Move(float vx, float vy, float vyaw) {
        MoveParameter move(vx, vy, vyaw);
        std::string param = move.ToJson().dump();
        return SendApiRequest(LocoApiId::kMove, param);
    }

    /**
     * @brief Send robot movement command without waiting for response
     *
     * @param vx linear velocity in x direction, unit: m/s
     * @param vy linear velocity in y direction, unit: m/s
     * @param vyaw angular velocity, unit: rad/s
     *
     * @return 0 if success, otherwise return error code
     * @note This method confirms transport submission only and is intended for
     * periodic velocity streaming.
     */
    int32_t MoveCommand(float vx, float vy, float vyaw) {
        MoveParameter move(vx, vy, vyaw);
        std::string param = move.ToJson().dump();
        return SendApiRequestFireAndForget(LocoApiId::kMove, param);
    }

    /**
     * @brief Robot rotates its head
     *
     * @param pitch pitch angle, unit: rad
     * @param yaw yaw angle, unit: rad
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t RotateHead(float pitch, float yaw) {
        RotateHeadParameter head_ctrl(pitch, yaw);
        std::string param = head_ctrl.ToJson().dump();
        return SendApiRequest(LocoApiId::kRotateHead, param);
    }

    /**
     * @brief Robot rotates its head to target position within specific time
     *
     * @param pitch target pitch angle, unit: rad
     * @param yaw target yaw angle, unit: rad
     * @param time_millis duration to reach the target, unit: ms
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t RotateHeadWithTime(float pitch, float yaw, int time_millis) {
        RotateHeadWithTimeParameter head_ctrl(pitch, yaw, time_millis);
        std::string param = head_ctrl.ToJson().dump();
        return SendApiRequest(LocoApiId::kRotateHeadWithTime, param);
    }

    /**
     * @brief Robot waves its hand
     * @note Supported model: K1 | T1 | T2
     * @note Start and stop supported model: K1 | T1
     * @note T2 supports start only and refuses kHandClose because its trajectory
     * completes automatically. The current T1_7DofArm factory configuration returns
     * kRpcStatusCodeServerRefused for both requests.
     *
     * @param action kHandOpen to start or kHandClose to stop.
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t WaveHand(HandAction action) {
        WaveHandParameter wave_hand(kRightHand, action);
        std::string param = wave_hand.ToJson().dump();
        return SendApiRequest(LocoApiId::kWaveHand, param);
    }

    /**
     * @brief Rotates the head continuously in the requested joint directions.
     *
     * @param pitch_direction Pitch-joint direction: `-1`, `0`, or `1` for
     * negative, stopped, or positive motion.
     * @param yaw_direction Yaw-joint direction: `-1`, `0`, or `1` for
     * negative, stopped, or positive motion.
     *
     * @return 0 if success, otherwise return error code
     * @note The service clamps motion at the configured head joint limits.
     */
    int32_t RotateHeadWithDirection(int pitch_direction, int yaw_direction) {
        RotateHeadWithDirectionParameter head_ctrl(pitch_direction, yaw_direction);
        std::string param = head_ctrl.ToJson().dump();
        return SendApiRequest(LocoApiId::kRotateHeadWithDirection, param);
    }

    /**
     * @brief Requests the model-configured lie-down trajectory.
     * @warning This API is unstable and may change in future releases.
     * @warning On the current K1 configuration, the service accepts this call
     * and dispatches a model-configured nested trajectory, but all currently
     * configured K1 nested-trajectory slots are placeholders. The call may
     * return success while commanding a zero-position trajectory instead of a
     * supported lie-down motion.
     * @return 0 if success, otherwise return error code
     * @note Standard T1 provides the intended lie-down trajectory and T2 uses
     * its model-specific trajectory. The current T1_7DofArm factory
     * configuration returns kRpcStatusCodeServerRefused.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t LieDown() {
        return SendApiRequest(LocoApiId::kLieDown, "");
    }

    /**
     * @brief The robot gets up
     * @note Supported model: K1 | T1 | T2
     * @note GetUpVersion::kV2 supported model: K1
     * @note T1_7DofArm disables hand actions and returns
     * kRpcStatusCodeServerRefused before version dispatch.
     *
     * @param version get-up behavior version, options are: kV1, kV2
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t GetUp(GetUpVersion version = GetUpVersion::kV1) {
        GetUpParameter param(version);
        std::string json = param.ToJson().dump();
        return SendApiRequest(LocoApiId::kGetUp, json);
    }

    /**
     * @brief The robot gets up to specified mode, either kWalking or kSoccer
     * @note Supported model: K1 | T1 | T2
     * @note GetUpVersion::kV2 supported model: K1
     * @note T2 supports kV1 with walking mode, but soccer mode is disabled on
     * T2. T1_7DofArm returns
     * kRpcStatusCodeServerRefused because hand actions are disabled.
     *
     * @param mode target mode after getting up, options are: kWalking, kSoccer
     * @param version get-up behavior version, options are: kV1, kV2
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t GetUpWithMode(booster::robot::RobotMode mode, GetUpVersion version = GetUpVersion::kV1) {
        GetUpWithModeParameter param(mode, version);
        std::string json = param.ToJson().dump();
        return SendApiRequest(LocoApiId::kGetUpWithMode, json);
    }

    /**
     * @brief The robot executes a powerful kicking motion.
     *
     * @return 0 if success, otherwise return error code
     * @note The RPC handler has no model-name gate. T1 provides the intended
     * shooting motion; a robot without a valid transition to that motion returns
     * kRpcStatusCodeStateTransitionFailed.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t Shoot() {
        return SendApiRequest(LocoApiId::kShoot, "");
    }

    /**
     * @brief Move hand end-effector to a target posture(position & orientation) with an auxiliary point
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     *
     * @param target_posture Represents the target posture in base frame (torso frame) that the hand end-effector should reach.
     * It contains position & orientation.
     * @param aux_posture Represents the auxiliary point on the end-effector's motion arc trajectory
     * @param time_millis Specifies the duration, in milliseconds, for completing the movement.
     * @param hand_index Identifies which hand the parameter refers to (for instance, left hand or right hand).
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t MoveHandEndEffectorWithAux(const Posture &target_posture, const Posture &aux_posture, int time_millis, HandIndex hand_index) {
        MoveHandEndEffectorParameter move_hand(target_posture, aux_posture, time_millis, hand_index);
        std::string param = move_hand.ToJson().dump();
        return SendApiRequest(LocoApiId::kMoveHandEndEffector, param);
    }

    /**
     * @brief Move hand end-effector with a target posture(position & orientation)
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     * @deprecated This API will be removed in a future version. Use
     * MoveHandEndEffectorV2() instead.
     * @param target_posture Represents the target posture in base frame (torso frame) that the hand end-effector should reach.
     * It contains position & orientation.
     * @param time_millis Specifies the duration, in milliseconds, for completing the movement.
     * @param hand_index Identifies which hand the parameter refers to (for instance, left hand or right hand).
     *
     * @return 0 if success, otherwise return error code
     *
     * @details
     * **Reason for deprecation**: This API is deprecated due to an implicit rotational offset (rot) being applied to the target orientation.
     * The final orientation is calculated as orientation = rot * offset, which contradicts the parameter description of `target_posture`.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t MoveHandEndEffector(const Posture &target_posture, int time_millis, HandIndex hand_index) {
        MoveHandEndEffectorParameter move_hand(target_posture, time_millis, hand_index, false);
        std::string param = move_hand.ToJson().dump();
        return SendApiRequest(LocoApiId::kMoveHandEndEffector, param);
    }

    /**
     * @brief Move hand end-effector with a target posture(position & orientation)
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     *
     * @param target_posture Represents the target posture in base frame (torso frame) that the hand end-effector should reach.
     * It contains position & orientation.
     * @param time_millis Specifies the duration, in milliseconds, for completing the movement.
     * @param hand_index Identifies which hand the parameter refers to (for instance, left hand or right hand).
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t MoveHandEndEffectorV2(const Posture &target_posture, int time_millis, HandIndex hand_index) {
        MoveHandEndEffectorParameter move_hand(target_posture, time_millis, hand_index, true);
        std::string param = move_hand.ToJson().dump();
        return SendApiRequest(LocoApiId::kMoveHandEndEffector, param);
    }

    /**
     * @brief Move dual hand end-effector to target postures(position & orientation)
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     *
     * @param left_target_posture Represents the target posture in base frame (torso frame) that the left hand end-effector should reach.
     * It contains position & orientation.
     * @param right_target_posture Represents the target posture in base frame (torso frame) that the right hand end-effector should reach.
     * It contains position & orientation.
     * @param time_millis Specifies the duration, in milliseconds, for completing the movement.
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t MoveDualHandEndEffector(
        const Posture &left_target_posture,
        const Posture &right_target_posture,
        int time_millis) {
        MoveDualHandEndEffectorParameter move_dual_hand(
            left_target_posture,
            right_target_posture,
            time_millis);
        std::string param = move_dual_hand.ToJson().dump();
        return SendApiRequest(LocoApiId::kMoveDualHandEndEffector, param);
    }

    /**
     * @brief Stop hand end-effector movement
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate. If the planner action is not
     * active, the service returns kRpcStatusCodeBadRequest.
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t StopHandEndEffector() {
        return SendApiRequest(LocoApiId::kStopHandEndEffector, "");
    }

    /**
     * @brief Control gripper
     * @note Supported model: K1 | T1 | T2
     * @note Requires a compatible gripper. Commands are refused in damping
     * mode.
     *
     * @param motion_param motion parameter, include position, force, velocity, see `GripperMotionParameter`
     * @param mode gripper control mode, options are: kPosition, kForce, see `GripperControlMode`
     * @param hand_index hand index, options are: kLeftHand, kRightHand
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t ControlGripper(const GripperMotionParameter &motion_param, GripperControlMode mode, HandIndex hand_index) {
        ControlGripperParameter control_gripper(motion_param, mode, hand_index);
        std::string param = control_gripper.ToJson().dump();
        return SendApiRequest(LocoApiId::kControlGripper, param);
    }

    /**
     * @brief Get frame transform
     *
     * @param src Source frame.
     * @param dst Destination frame.
     * @param[out] transform Calculated transform from `src` to `dst`.
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t GetFrameTransform(Frame src, Frame dst, Transform &transform) {
        GetFrameTransformParameter frame_transform(src, dst);
        std::string param = frame_transform.ToJson().dump();
        Response resp;
        int32_t ret = SendApiRequestWithResponse(LocoApiId::kGetFrameTransform, param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        transform.FromJson(body_json);
        return 0;
    }

    /**
     * @brief Switches hand end-effector control mode on the legacy service backend.
     *
     * @param switch_on true to switch on, false to switch off
     *
     * @return 0 if success, otherwise return error code
     * @deprecated The robot-state-manager RPC handler does not implement this ID
     * and returns kRpcStatusCodeBadRequest. The legacy LocoApiService handler
     * does implement it. Do not rely on this method unless the active server
     * backend is known.
     */
    int32_t SwitchHandEndEffectorControlMode(bool switch_on) {
        SwitchHandEndEffectorControlModeParameter switch_param(switch_on);
        std::string param = switch_param.ToJson().dump();
        return SendApiRequest(LocoApiId::kSwitchHandEndEffectorControlMode, param);
    }

    /**
     * @brief Handshake
     *
     * @param action whether to start handshake action, options are: kHandOpen, kHandClose
     *
     * @return 0 if success, otherwise return error code
     * @note The RPC handler has no model-name gate. A factory configuration
     * with this action disabled, including the current T1_7DofArm
     * configuration, returns kRpcStatusCodeServerRefused. An unavailable
     * action transition returns kRpcStatusCodeStateTransitionFailed.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t Handshake(HandAction action) {
        HandshakeParameter handshake(action);
        std::string param = handshake.ToJson().dump();
        return SendApiRequest(LocoApiId::kHandshake, param);
    }

    /**
     * @brief Make the robot perform a hand-on-chest greeting
     * @note Supported model: T2
     * @note A lower request is accepted only while the raised greeting
     * trajectory is active.
     *
     * @param up true to raise the hand to the chest, false to lower it
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t HandOnChestGreeting(bool up) {
        HandOnChestGreetingParameter greeting_param(up);
        std::string param = greeting_param.ToJson().dump();
        return SendApiRequest(LocoApiId::kHandOnChestGreeting, param);
    }

    /**
     * @brief Control dexterous hand
     * @note Supported model: K1 | T1 | T2
     * @note Requires a compatible dexterous hand. Commands are refused in
     * damping mode.
     *
     * @param finger_params finger parameters, include position, force, speed, see `DexterousFingerParameter`
     * @param hand_index hand index, options are: kLeftHand, kRightHand
     * @param hand_type hand type, options are: kInspireHand, kInspireTouchHand, kRevoHand
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t ControlDexterousHand(const std::vector<DexterousFingerParameter> &finger_params, HandIndex hand_index, BoosterHandType hand_type = BoosterHandType::kInspireHand) {
        ControlDexterousHandParameter control_dexterous_hand(finger_params, hand_index, hand_type);
        std::string param = control_dexterous_hand.ToJson().dump();
        return SendApiRequest(LocoApiId::kControlDexterousHand, param);
    }

    /**
     * @brief Make the robot perform a dance.
     * @note Supported model: K1 | T1
     * @note A disabled shared action capability returns
     * kRpcStatusCodeServerRefused; if the configured planner cannot be started
     * or updated, the service returns kRpcStatusCodeStateTransitionFailed.
     *
     * @param dance_id The identifier of the dance to be performed
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t Dance(DanceId dance_id) {
        DanceParameter dance(dance_id);
        std::string param = dance.ToJson().dump();
        return SendApiRequest(LocoApiId::kDance, param);
    }

    /**
     * @brief Plays an audio file through the robot sound service.
     * @note Supported model: K1 | T1 | T2
     * @note Requires the sound service and output hardware.
     *
     * @param sound_file_path Non-empty path accessible to the robot service.
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t PlaySound(const std::string &sound_file_path) {
        PlaySoundParameter play_sound(sound_file_path);
        std::string param = play_sound.ToJson().dump();
        return SendApiRequest(LocoApiId::kPlaySound, param);
    }

    /**
     * @brief Stop sound
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t StopSound() {
        return SendApiRequest(LocoApiId::kStopSound, "");
    }

    /**
     * @brief Enable or disable zero torque drag, depending on active state
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     *
     * @param active true to enable, false to disable
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t ZeroTorqueDrag(bool active) {
        ZeroTorqueDragParameter zero_torque_drag(active);
        std::string param = zero_torque_drag.ToJson().dump();
        return SendApiRequest(LocoApiId::kZeroTorqueDrag, param);
    }

    /**
     * @brief Start or stop recording trajectory, depending on active state
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     *
     * @param active true to start recording, false to stop
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t RecordTrajectory(bool active) {
        RecordTrajectoryParameter record_trajectory(active);
        std::string param = record_trajectory.ToJson().dump();
        return SendApiRequest(LocoApiId::kRecordTrajectory, param);
    }

    /**
     * @brief Replay trajectory
     * @note Supported model: K1 | T1
     * @note The handler has no model-name gate; if the configured planner
     * cannot be started or updated, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     *
     * @param path Trajectory file path accessible to the robot service.
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t ReplayTrajectory(std::string path) {
        ReplayTrajectoryParameter replay_trajectory(path);
        std::string param = replay_trajectory.ToJson().dump();
        return SendApiRequest(LocoApiId::kReplayTrajectory, param);
    }

    /**
     * @brief Make the robot perform a whole body dance.
     * @note Supported model: K1 | T2
     * @note Values through WholeBodyDanceId::kMichaelDance1And2 supported model: K1
     * @note WholeBodyDanceId::kBowAndArrow and kCharlestonDance supported model: T2
     *
     * @param dance_id The identifier of the whole body dance to be performed
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t WholeBodyDance(WholeBodyDanceId dance_id) {
        WholeBodyDanceParameter dance_param(dance_id);
        std::string param = dance_param.ToJson().dump();
        return SendApiRequest(LocoApiId::kWholeBodyDance, param);
    }

    /**
     * @brief Make the UpperBodyCustomControl action start or stop.
     * @note Supported model: K1 | T1 | T2
     * @note Low-level commands must use the matching model-specific joint
     * layout from b1_api_const.hpp.
     *
     * @param start true to start the action, false to stop it
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t UpperBodyCustomControl(bool start) {
        UpperBodyCustomControlParameter upper_body_param(start);
        std::string param = upper_body_param.ToJson().dump();
        return SendApiRequest(LocoApiId::kUpperBodyCustomControl, param);
    }

    /**
     * @brief Reset the robot's odometry
     * @return 0 if success, otherwise return error code
     */
    int32_t ResetOdometry() {
        return SendApiRequest(LocoApiId::kResetOdometry, "");
    }

    /**
     * @brief Loads a custom trained trajectory and its model configuration.
     * @note Supported model: K1 | T2
     *
     * @param traj Trajectory file, model file, gains, scales, and joint-order
     * configuration.
     * @param[out] tid Service-assigned trajectory identifier used by activate
     * and unload operations.
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t LoadCustomTrainedTraj(const CustomTrainedTraj &traj, std::string &tid) {
        std::string param = traj.ToJson().dump();
        Response resp;
        int32_t ret = SendApiRequestWithResponse(LocoApiId::kLoadCustomTrainedTraj, param, resp);
        if (ret != 0) {
            return ret;
        }

        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        LoadCustomTrainedTrajResponse load_resp;
        load_resp.FromJson(body_json);
        tid = load_resp.tid_;

        return 0;
    }

    /**
     * @brief Activate a loaded custom trained trajectory
     * @note Supported model: K1 | T2
     *
     * @param tid The trajectory ID to activate
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t ActivateCustomTrainedTraj(const std::string &tid) {
        CustomTrainedTrajParameter param_obj(tid);
        std::string param = param_obj.ToJson().dump();
        return SendApiRequest(LocoApiId::kActivateCustomTrainedTraj, param);
    }

    /**
     * @brief Unload a custom trained trajectory
     * @note Supported model: K1 | T2
     *
     * @param tid The trajectory ID to unload
     *
     * @return 0 if success, otherwise return error code
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t UnloadCustomTrainedTraj(const std::string &tid) {
        CustomTrainedTrajParameter param_obj(tid);
        std::string param = param_obj.ToJson().dump();
        return SendApiRequest(LocoApiId::kUnloadCustomTrainedTraj, param);
    }

    /**
     * @brief Get trained trajectory runtime status (custom or built-in)
     * @note Supported model: K1 | T1 | T2
     * @note T1 does not execute the trained-trajectory body controller and
     * normally reports idle.
     *
     * @param[out] response status / traj_id
     *
     * @return 0 if success, otherwise return error code
     */
    int32_t GetTrainedTrajStatus(GetTrainedTrajStatusResponse &response) {
        std::string param{};
        Response resp;
        int32_t ret = SendApiRequestWithResponse(LocoApiId::kGetTrainedTrajStatus,
                                                 param, resp);
        if (ret != 0) {
            return ret;
        }
        nlohmann::json body_json = nlohmann::json::parse(resp.GetBody());
        response.FromJson(body_json);
        return ret;
    }

    /**
     * @brief Enter wbc gait
     *
     * @return 0 if success, otherwise return error code
     * @note No model-name gate is applied. If the configured WBC gait cannot be
     * entered, the service returns kRpcStatusCodeStateTransitionFailed. Current
     * K1 factory software provides this path.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t EnterWBCGait() {
        return SendApiRequest(LocoApiId::kEnterWBCGait, "");
    }

    /**
     * @brief Exit WBC Gait
     *
     * @return 0 if success, otherwise return error code
     * @note No model-name gate is applied. If the configured humanlike gait
     * cannot be entered, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t ExitWBCGait() {
        return SendApiRequest(LocoApiId::kExitWBCGait, "");
    }

    /**
     * @brief Start or stop visual side-foot kick
     *
     * @param start true to start visual kick, false to stop
     * @param version visual kick version, options are: kV1, kV2
     *
     * @return 0 if success, otherwise return error code
     * @note Neither version is rejected by model name. kV1 requests the base
     * visual-kick path. kV2 uses the WBC path where enabled by the factory
     * software and otherwise falls back to the configured non-WBC path. T1/T2
     * may therefore accept the request, but missing or unreachable motions return
     * kRpcStatusCodeStateTransitionFailed.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t VisualKick(bool start, VisualKickVersion version = VisualKickVersion::kV1) {
        VisualKickParameter parameter(start, version);
        std::string param = parameter.ToJson().dump();
        return SendApiRequest(LocoApiId::kVisualKick, param);
    }

    /**
     * @brief Lion dance prepare
     *
     * @details State transition rules:
     * - Allowed entry from: Walking mode.
     * - Allowed transition to: LionDanceMove or LionDanceStart.
     *
     * @param start true to enter Lion Dance prepare pose, false to exit.
     * @return 0 if success, otherwise return error code
     * @note The current K1 factory software provides the required lion-dance
     * motion. The handler has no model-name gate; if the configured motion or
     * transition is unavailable, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     * @note When preparation uses an asynchronous intermediate transition, a
     * successful response confirms that the intermediate transition was
     * scheduled; it does not guarantee that the final preparation pose was
     * entered. Failure to release the fixed-arm state returns
     * kRpcStatusCodeInternalServerError.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t LionDancePrepare(bool start) {
        LionDancePrepareParameter param(start);
        std::string json = param.ToJson().dump();
        return SendApiRequest(LocoApiId::kLionDancePrepare, json);
    }

    /**
     * @brief Lion dance start
     *
     * @details State transition rules:
     * - Allowed entry from: LionDancePrepare or LionDanceMove ONLY.
     *
     * @warning
     * STRICTLY PROHIBITED to enter from any other state. Doing so will
     * cause abrupt joint jumping (discontinuity) in the arm actuators,
     * which poses a safety risk and may damage the hardware.
     *
     * @param dance_id The specific ID of the lion dance.
     * @return 0 if success, otherwise return error code
     * @note The current K1 factory software provides the required lion-dance
     * motion. The handler has no model-name gate; if the configured motion or
     * transition is unavailable, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     * @note Failure to apply the required fixed-arm state returns
     * kRpcStatusCodeInternalServerError before the motion is requested.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t LionDanceStart(int dance_id) {
        LionDanceStartParameter param(dance_id);
        std::string json = param.ToJson().dump();
        return SendApiRequest(LocoApiId::kLionDanceStart, json);
    }

    /**
     * @brief Lion dance move
     *
     * @details State transition rules:
     * - Allowed entry from: LionDancePrepare and Walk Gait.
     * - Allowed transition to: LionDanceStart.
     *
     * @param start True to start movement synchronization, false to stop.
     * @return 0 if success, otherwise return error code
     * @note The current K1 factory software provides the required lion-dance
     * motion. The handler has no model-name gate; if the configured motion or
     * transition is unavailable, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     * @note Failure to change the required fixed-arm state returns
     * kRpcStatusCodeInternalServerError.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t LionDanceMove(bool start) {
        LionDanceMoveParameter param{start};
        std::string json = param.ToJson().dump();
        return SendApiRequest(LocoApiId::kLionDanceMove, json);
    }

    /**
     * @brief Switch robot gait type
     *
     * @param gait_type gait type, options are:
     * kWholeBodyHumanlikeGait, kHalfBodyHumanlikeGait, kHalfBodyHumanlikeGaitV2,
     * kWholeBodyHumanlikeGaitV2
     *
     * @return 0 if success, otherwise return error code
     * @note The server maps each GaitType to a body control without a model-name
     * gate. Current graphs broadly provide kHalfBodyHumanlikeGaitV2, while the
     * other values are primarily configured on K1. If the mapped body control
     * cannot be selected, the service returns
     * kRpcStatusCodeStateTransitionFailed.
     * @see @ref b1_loco_model_support_matrix
     */
    int32_t SwitchGait(GaitType gait_type) {
        SwitchGaitParameter param(gait_type);
        std::string json = param.ToJson().dump();
        return SendApiRequest(LocoApiId::kSwitchGait, json);
    }

private:
    std::shared_ptr<RpcClient> rpc_client_; ///< Underlying locomotion RPC transport.
};

}
}
} // namespace booster::robot::b1

#endif // __BOOSTER_ROBOTICS_SDK_B1_LOCO_CLIENT_HPP__
