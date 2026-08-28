#pragma once

namespace booster {
namespace robot {

/** @brief High-level robot operating mode; supported transitions are model-specific. */
enum class RobotMode {
    kUnknown = -1, ///< Unknown mode, used for error handling.
    kDamping = 0,  ///< Put all motors into damping mode; the robot may fall.
    kPrepare = 1,  ///< Maintain a two-foot standing posture before walking.
    kWalking = 2,  ///< Enable locomotion and walking-mode actions.
    kCustom = 3,   ///< Enable custom body controls and actions.
    kSoccer = 4,   ///< Enable soccer locomotion and actions; supported model: K1 | T1.
};

/** @brief Body controller selected within a robot mode. */
enum class BodyControl {
    kUnknown = 0,               ///< Unknown or unavailable body controller.
    kDamping = 1,               ///< Damping-mode controller.
    kPrepare = 2,               ///< Prepare-mode standing controller.
    kHumanlikeGait = 3,         ///< Human-like walking controller.
    kProneBody = 4,             ///< Prone-posture controller for lying down and push-ups.
    kSoccerGait = 5,            ///< Soccer locomotion controller.
    kCustom = 6,                ///< Custom-mode controller.
    kGetUp = 7,                 ///< Controller for recovering from a prone posture.
    kWholeBodyDance = 8,        ///< Whole-body dance controller.
    kShoot = 9,                 ///< Powerful soccer-shot controller.
    kInsideFoot = 10,           ///< Legacy name for the visual-kick V2 controller.
    kGoalie = 11,               ///< Soccer goalkeeper controller.
    kWBCGait = 12,              ///< Whole-body-control gait controller.
    kLionDancePreparePose = 13, ///< Lion-dance preparation-pose controller.
    kVisualKickV1 = 14,         ///< Visual-kick V1 controller.
};

/** @brief Built-in gesture, dance and trajectory actions. */
enum class Action {
    kUnknown = 0,            ///< Unknown or unavailable action.
    kHandShake = 1,          ///< Handshake action.
    kHandWave = 2,           ///< Hand-waving action.
    kHandControl = 3,        ///< Hand end-effector control action.
    kDanceNewYear = 4,       ///< New Year dance.
    kDanceNezha = 5,         ///< Nezha dance.
    kDanceTowardsFuture = 6, ///< Towards the Future dance.
    kGestureDabbing = 7,     ///< Dabbing gesture.
    kGestureUltraman = 8,    ///< Ultraman gesture.
    kGestureRespect = 9,     ///< Respect gesture.
    kGestureCheer = 10,      ///< Cheering gesture.
    kGestureLuckyCat = 11,   ///< Lucky-cat gesture.
    kGestureBoxing = 12,     ///< Boxing gesture.
    kZeroTorqueDrag = 13,    ///< Zero-torque arm-drag action.
    kRecordTraj = 14,        ///< Trajectory-recording action.
    kRunRecordedTraj = 15,   ///< Recorded-trajectory replay action.
};

/** @brief Reference frame used by pose or motion APIs. */
enum class Frame {
    kUnknown = -1, ///< Unknown frame, used for error handling.
    kBody = 0,     ///< Robot body frame.
    kHead = 1,     ///< Robot head frame.
    kLeftHand = 2, ///< Left-hand frame.
    kRightHand = 3, ///< Right-hand frame.
    kLeftFoot = 4, ///< Left-foot frame.
    kRightFoot = 5, ///< Right-foot frame.
};

/** @brief Sub-state of prone-body control. */
enum class ProneBodyControlPosture {
    kUnknown = 0,          ///< Unknown prone-controller posture.
    kInactive = 1,         ///< Prone-body control is inactive.
    kPushUp = 2,           ///< Push-up posture or activity.
    kLieDown = 3,          ///< Lying-down posture.
    kSoccerLocomotion = 4, ///< Soccer locomotion posture.
    kSoccerKicking = 5,    ///< Soccer kicking posture.
};

/** @brief RoboCup behavior execution state. */
enum class RobocupBehaviorStatus {
    RUNNING = 0,  ///< Behavior execution is in progress.
    SHOOTING = 1, ///< The robot is executing a shot.
    PASSING = 2,  ///< The robot is executing a pass.
};

/** @brief Status of a custom or built-in trained trajectory. */
enum class TrainedTrajStatus {
    kIdle = 0,    ///< No trained trajectory is executing.
    kRunning = 1, ///< A trained trajectory is executing.
};

}
} // namespace booster::robot
