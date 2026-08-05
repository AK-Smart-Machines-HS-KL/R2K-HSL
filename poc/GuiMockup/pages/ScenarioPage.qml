import QtQuick
import Theme
import "../panel"

Item {
    anchors.fill: parent
    Column {
        anchors.centerIn: parent; spacing: 16
        Text { text: "SCENARIO"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
        CardStrip {
            width: parent.width
            height: Theme.cardHeight
            items: Bridge.scenarioRepo.names()
            selectedName: Bridge.backend.selected_scenario
            onSelected: (name) => Bridge.backend.select_scenario(name)
        }
    }
}
