import QtQuick
import Theme
import "../panel"

Item {
    anchors.fill: parent
    Component.onCompleted: Bridge.modelRepo.refresh()
    Column {
        anchors.centerIn: parent; spacing: 16
        Text { text: "MODEL"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
        CardStrip {
            width: parent.width
            height: Theme.cardHeight
            items: Bridge.modelRepo.names()
            selectedName: Bridge.backend.selected_model
            onSelected: (name) => Bridge.backend.select_model(name)
        }
    }
}
