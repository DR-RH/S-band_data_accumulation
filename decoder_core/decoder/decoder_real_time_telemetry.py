import struct

from decoder import decoder_main_HK


MAIN_PIC_TLM_SIZE = 191
COM_PIC_TLM_SIZE = 11
REALTIME_TLM_SIZE = MAIN_PIC_TLM_SIZE + COM_PIC_TLM_SIZE


def process_com_pic_telemetry(com_pic_tlm: bytes) -> dict:
    if len(com_pic_tlm) < COM_PIC_TLM_SIZE:
        raise ValueError(
            f"COM PIC telemetry must be at least {COM_PIC_TLM_SIZE} bytes, "
            f"got {len(com_pic_tlm)}"
        )

    (
        ok_to_transmit_auto_packet,
        transmit_carrier,
        antenna_ack,
        antenna_auto_packet,
        antenna_downlink,
        power_ack,
        power_auto_packet,
        power_downlink,
        sband_tx_bitrate,
        _footer,
        current_slot,
    ) = struct.unpack("<11B", com_pic_tlm[:COM_PIC_TLM_SIZE])

    antenna_map = {1: "directional", 2: "omni"}
    power_map = {0: "low", 1: "high"}
    bitrate_map = {
        0: "10kbps",
        1: "20kbps",
        2: "25kbps",
        3: "50kbps",
        4: "64kbps",
        5: "100kbps",
        6: "250kbps",
        7: "500kbps",
    }

    return {
        "ok_to_transmit_auto_packet": ok_to_transmit_auto_packet,
        "transmit_carrier": transmit_carrier,
        "antenna_ack": antenna_map.get(antenna_ack, f"unknown({antenna_ack})"),
        "antenna_auto_packet": antenna_map.get(
            antenna_auto_packet, f"unknown({antenna_auto_packet})"
        ),
        "antenna_downlink": antenna_map.get(
            antenna_downlink, f"unknown({antenna_downlink})"
        ),
        "power_ack": power_map.get(power_ack, f"unknown({power_ack})"),
        "power_auto_packet": power_map.get(
            power_auto_packet, f"unknown({power_auto_packet})"
        ),
        "power_downlink": power_map.get(power_downlink, f"unknown({power_downlink})"),
        "sband_tx_bitrate": bitrate_map.get(
            sband_tx_bitrate, f"unknown({sband_tx_bitrate})"
        ),
        "current_slot": current_slot,
    }


def process_realtime_telemetry(main_pic_tlm: bytes, com_pic_tlm: bytes) -> dict:
    main_rows = decoder_main_HK.decode(main_pic_tlm)
    if not main_rows:
        raise ValueError("Main PIC telemetry did not contain a valid 191-byte HK chunk")

    parameters = dict(main_rows[0])
    parameters.update(process_com_pic_telemetry(com_pic_tlm))
    return parameters


def decode(data: bytes) -> list[dict]:
    parameters_array = []

    chunks = [
        data[i : i + REALTIME_TLM_SIZE]
        for i in range(0, len(data), REALTIME_TLM_SIZE)
    ]
    for chunk in chunks:
        if len(chunk) < REALTIME_TLM_SIZE:
            continue

        main_pic_tlm = chunk[:MAIN_PIC_TLM_SIZE]
        com_pic_tlm = chunk[MAIN_PIC_TLM_SIZE:REALTIME_TLM_SIZE]
        parameters_array.append(process_realtime_telemetry(main_pic_tlm, com_pic_tlm))

    return parameters_array
