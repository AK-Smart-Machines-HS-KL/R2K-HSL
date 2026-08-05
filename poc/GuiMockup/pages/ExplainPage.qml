import QtQuick
import Theme
import "../components"

Item {
    anchors.fill: parent
    Column {
        anchors.centerIn: parent; spacing: 16
        Text { text: "EXPLAIN MODE"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter; spacing: 16
            ChoiceCard {
                entryLabel: "Assignments Only"
                entryName: "Fast, minimal output"
                selected: !Bridge.backend.explain_enabled
                onClicked: Bridge.backend.set_explain(false)
            }
            ChoiceCard {
                entryLabel: "Full Analysis"
                entryName: "Shows AI reasoning, oracle, strategy"
                selected: Bridge.backend.explain_enabled
                onClicked: Bridge.backend.set_explain(true)
            }
        }
    }
}
