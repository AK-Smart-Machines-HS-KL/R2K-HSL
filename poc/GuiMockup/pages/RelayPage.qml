import QtQuick
import Theme
import "../panel"

Item {
    anchors.fill: parent
    property var relayItems: [
        { name: "only_sim_bots",   label: "Simulation Only" },
        { name: "hardware_mirror", label: "Hardware Mirror" }
    ]

    Column {
        anchors.centerIn: parent; spacing: 16
        Text { text: "RELAY"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
        CardStrip {
            width: parent.width
            height: Theme.cardHeight
            items: relayItems
            showArrows: false
            stripSpacing: 16
            selectedName: Bridge.backend.selected_relay
            onSelected: (name) => Bridge.backend.select_relay(name)
        }
    }
}
