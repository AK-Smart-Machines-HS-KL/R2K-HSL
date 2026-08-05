import QtQuick
import Theme
import "../components"

Item {
    anchors.fill: parent
    Column {
        anchors.centerIn: parent; spacing: 16
        Text { text: "DISPLAY MODE"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter; spacing: 16
            ChoiceCard {
                entryLabel: "Headless Mode"
                entryName: "gzserver only, no GUI"
                selected: Bridge.backend.headless_enabled
                onClicked: Bridge.backend.set_headless(true)
            }
            ChoiceCard {
                entryLabel: "Visual Mode"
                entryName: "Gazebo GUI + Visualizer"
                selected: !Bridge.backend.headless_enabled
                onClicked: Bridge.backend.set_headless(false)
            }
        }
    }
}
