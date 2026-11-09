std_msgs/Header header

# Decoded RoboCupGameControlData (HSL GameController, struct version 20).
# Published at the GC's control broadcast rate (~2 Hz) on /gc/game_state.
# All enums mirror the upstream RoboCupGameControlData.h defines.

uint8 packet_number
uint8 players_per_team
uint8 competition_type   # COMPETITION_TYPE_SMALL=0 MIDDLE=1 LARGE=2
bool  stopped
uint8 game_phase         # GAME_PHASE_NORMAL=0 PENALTY_SHOOT_OUT=1 EXTRA_TIME=2 TIMEOUT=3
uint8 state              # STATE_INITIAL=0 READY=1 SET=2 PLAYING=3 FINISHED=4
uint8 set_play           # SET_PLAY_NONE=0 .. CORNER_KICK=6
bool  first_half
uint8 kicking_team        # team number, KICKING_TEAM_NONE=255
int16 secs_remaining
int16 secondary_time

# Both teams (index 0 = first/home, 1 = second/away).
uint8[2] team_number
uint8[2] score
uint16[2] message_budget

# The receiving player's own penalty entry (selected by --player / --team).
uint8 penalty                # PENALTY_NONE=0 .. PENALTY_SUBSTITUTE=13
uint8 secs_till_unpenalised
