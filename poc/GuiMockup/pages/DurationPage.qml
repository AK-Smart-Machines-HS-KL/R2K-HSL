import QtQuick
import QtQuick.Controls
import Theme

Item {
    anchors.fill: parent
    Column {
        anchors.centerIn: parent; spacing: 16; width: parent.width - 60
        Text { text: "DURATION"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
        Slider {
            width: parent.width; from: 10; to: 600; stepSize: 10
            anchors.horizontalCenter: parent.horizontalCenter
            value: Bridge.backend.duration_seconds
            onMoved: Bridge.backend.set_duration(Math.round(value))
            handle: Rectangle {
                x: parent.leftPadding + parent.visualPosition * (parent.availableWidth - width)
                y: parent.topPadding + parent.availableHeight / 2 - height / 2
                width: 18; height: 18; radius: 9
                color: Theme.accentColor
                border.color: Theme.accentDarker; border.width: 1
            }
            background: Rectangle {
                x: parent.leftPadding
                y: parent.topPadding + parent.availableHeight / 2 - 2
                width: parent.availableWidth; height: 4; radius: 2
                color: Theme.cardBorderColor
                Rectangle {
                    width: parent.parent.visualPosition * parent.width; height: parent.height; radius: 2
                    color: Theme.accentColor
                }
            }
        }
        Item { width: 1; height: 2 }
        Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: 8
            TextField {
                id: durInput; width: 70
                text: Bridge.backend.duration_seconds
                color: Theme.textColor; font.pixelSize: Theme.bodyPixel
                validator: IntValidator { bottom: 10; top: 600 }
                onEditingFinished: Bridge.backend.set_duration(parseInt(text) || 10)
                background: Rectangle { radius: 4; color: Theme.backgroundColor; border.color: durInput.activeFocus ? Theme.accentColor : Theme.cardBorderColor; border.width: 1 }
            }
            Text { text: "seconds"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; anchors.verticalCenter: parent.verticalCenter }
        }
    }
}
