from collections import namedtuple
# constants for status parameters

STA_OFFON = (
    "OFF",
    "ON"
)
STA_NOYES = (
    "NO",
    "YES"
)
STA_BOOT_RELAY = (
    "Redundant",
    "ILLEGAL",
    "ILLEGAL",
    "Primary"
)
STA_WDT_ENABLE = (
    "Disabled",
    "Enabled"
)
STA_WDT_EVENT = (
    "No Reset",
    "Reset Occurred"
)
STA_ARMED_STATUS = (
    "Not Armed",
    "Armed"
)
STA_VALID = (
    "Invalid",
    "Valid"
)
STA_ST_ID_STATUS = (
    "IDLE",
    "INITIALIZE",
    "WAITING_FOR_IMAGE1",
    "WAITING_FOR_IMAGE2",
    "CALUCLATE_RATE",
    "MAKE_UNIT_VECTORS",
    "AWAITING_TRISTAR",
    "OK_Found_4",
    "OK_Found_3",
    "TIMEOUT",
    "ILLEGAL",
    "NO_MATCH"
)
STA_ST_ATT_STATUS = (
    "OK",
    "PENDING", 
    "BAD",
    "TOO_FEW_STARS",
    "QUEST_FAILED",
    "RESIDUALS_TOO_HIGH",
    "TOO_CLOSE_TO_EDGE",
    "PIX_AMP_TOO_LOW",
    "PIX_AMP_TOO_HIGH",
    "BACKGND_TOO_HIGH",
    "TRACK_FAILURE",
    "PIX_SUM_TOO_LOW",
    "UNUSED",
    "TOO_DIM_FOR_STARID",
    "TOO_MANY_GROUPS",
    "TOO_FEW_GROUPS",
    "CHANNEL_DISABLED",
    "TRACK_BLK_OVERLAP",
    "OK_FOR_STARID",
    "TOO_CLOSE_TO_OTHER"
)
STA_SUN_POINT_STATE = (
    "SUN_POINT",
    "FINE_REF_POINT",
    "SEARCH_INIT",
    "SEARCHING",
    "WAITING",
    "CONVERGING",
    "ON_SUN",
    "NOT_ACTIVE"
)
STA_ADCSMODE = (
    "SUN_POINT",
    "FINE_REF_POINT"
)
STA_SUNPOINT_REASON = (
    "BOOT",
    "COMMAND",
    "ATTITUDE_INVALID",
    "TIME_INVALID",
    "REFS_INVALID"
)

# name, start_byte, bit_shift, fmt,  scale, status_strings

adcs_HK_list = [
    ["3V3 status",1,0,"1",1,STA_OFFON],
    ["12V low power status",1,1,"1",1,STA_OFFON],
    ["12V high power status",1,2,"1",1,STA_OFFON],
    ["12VH current",1,3,"B",1,None],
    ["12VL current",2,3,"B",1,None],
    ["Boot Relay Status",3,3,"2",1,STA_BOOT_RELAY],
    ["Watchdog Reset Enable Status",3,5,"1",1,STA_WDT_ENABLE],
    ["Watchdog Reset Event Status",3,6,"1",1,STA_WDT_EVENT],
    ["Processor reset arm status",3,7,"1",1,STA_ARMED_STATUS],
    ["TAI_SECONDS",4,0,"I",1,None],
    ["GPS_VALID",8,0,"1",1,STA_VALID],
    ["REFS_VALID",8,1,"1",1,STA_VALID],
    ["EARTH_PENUMBRA_UMBRA",8,2,"1",1,STA_NOYES],
    ["MAG_SOURCE_USED",8,3,"B",1,None],
    ["ATT_STATUS",9,3,"B",1,STA_ST_ATT_STATUS],
    ["ID_STATUS",10,3,"B",1,STA_ST_ID_STATUS],
    ["NUM_ATTITUDE_STARS",11,3,"B",1,None],
    ["INERTIA_INDEX",12,3,"B",1,None],
    ["SUN_POINT_STATE",13,3,"B",1,STA_SUN_POINT_STATE],
    ["CMD_ACCEPT_COUNT",14,3,"B",1,None],
    ["CMD_REJECT_COUNT",15,3,"B",1,None],
    ["POSITION_WRT_ECI_1",16,3,"h",1,None],
    ["POSITION_WRT_ECI_2",18,3,"h",1,None],
    ["POSITION_WRT_ECI_3",20,3,"h",1,None],
    ["VELOCITY_WRT_ECI_1",22,3,"h",1/1024,None],
    ["VELOCITY_WRT_ECI_2",24,3,"h",1/1024,None],
    ["VELOCITY_WRT_ECI_3",26,3,"h",1/1024,None],
    ["MAG_MODEL_VECTOR_BODY_1",28,3,"h",5e-9,None],
    ["MAG_MODEL_VECTOR_BODY_2",30,3,"h",5e-9,None],
    ["MAG_MODEL_VECTOR_BODY_3",32,3,"h",5e-9,None],
    ["MAG_POWER_STATE",34,3,"1",1,STA_OFFON],
    ["MAG_VECTOR_VALID",34,4,"1",1,STA_VALID],
    ["MAG_VECTOR_ENABLED",34,5,"1",1,STA_NOYES],
    ["MAG_TEST_MODE",34,6,"1",1,STA_NOYES],
    ["MAG_SENSOR_USED",34,7,"3",1,None],
    ["SUN_VECTOR_BODY_1",35,2,"h",0.0001,None],
    ["SUN_VECTOR_BODY_2",37,2,"h",0.0001,None],
    ["SUN_VECTOR_BODY_3",39,2,"h",0.0001,None],
    ["CSS_POWER_STATE",41,2,"1",1,STA_OFFON],
    ["MEAS_SUN_VALID",41,3,"1",1,STA_VALID],
    ["SUN_VECTOR_ENABLED",41,4,"1",1,STA_NOYES],
    ["CSS_TEST_MODE",41,5,"1",1,STA_NOYES],
    ["SUN_SENSOR_USED",41,6,"3",1,None],
    ["Q_BODY_WRT_ECI_1",42,1,"h",3.2768e-05,None],
    ["Q_BODY_WRT_ECI_2",44,1,"h",3.2768e-05,None],
    ["Q_BODY_WRT_ECI_3",46,1,"h",3.2768e-05,None],
    ["Q_BODY_WRT_ECI_4",48,1,"h",3.2768e-05,None],
    ["ATTITUDE_VALID",50,1,"1",1,STA_VALID],
    ["MEAS_ATT_VALID",50,2,"1",1,STA_VALID],
    ["MEAS_RATE_VALID",50,3,"1",1,STA_VALID],
    ["IMU_DATA_VALID",50,4,"1",1,STA_VALID],
    ["TRACKER_1DATA_VALID",50,5,"1",1,STA_VALID],
    ["BODY_RATE_1",50,6,"h",3.2768e-04,None],
    ["BODY_RATE_2",52,6,"h",3.2768e-04,None],
    ["BODY_RATE_3",54,6,"h",3.2768e-04,None],
    ["OPERATING_MODE_1",56,6,"B",1,None],
    ["OPERATING_MODE_2",57,6,"B",1,None],
    ["OPERATING_MODE_3",58,6,"B",1,None],
    ["FILTERED_SPEED_RPM_1",59,6,"h",131.0720,None],
    ["FILTERED_SPEED_RPM_2",61,6,"h",131.0720,None],
    ["FILTERED_SPEED_RPM_3",63,6,"h",131.0720,None],
    ["MOTOR_1TEMP",65,6,"b",1.28,None],
    ["MOTOR_2TEMP",66,6,"b",1.28,None],
    ["MOTOR_3TEMP",67,6,"b",1.28,None],
    ["ADCS_MODE",68,6,"1",1,STA_ADCSMODE],
    ["RECOMMEND_SUN_POINT",68,7,"1",1,STA_NOYES],
    ["SUN_POINT_REASON",69,0,"3",1,STA_SUNPOINT_REASON],
    ["ATT_CTRL_ACTIVE",69,3,"1",1,STA_NOYES],
    ["MOMENTUM_TOO_HIGH",69,4,"1",1,STA_NOYES],
    ["ON_SUN_FLAG",69,5,"1",1,STA_NOYES],
    ["SUN_AVOID_FLAG",69,6,"1",1,STA_NOYES],
    ["SUN_SOURCE_FAILOVER",69,7,"1",1,STA_NOYES],
    ["SUN_POINT_ANGLE_ERROR",70,0,"h",0.003,None],
    ["EIGEN_ERROR",72,0,"h",1/1024,None],
]


