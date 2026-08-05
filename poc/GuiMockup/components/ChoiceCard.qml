import QtQuick
import QtQuick.Controls
import Theme

Button {
    id: root
    property string entryName: ""
    property string entryLabel: ""
    property bool selected: false

    width: Theme.cardWidth
    height: Theme.cardHeight
    enabled: true
    hoverEnabled: true

    contentItem: Item {
        anchors.fill: parent
        anchors.margins: 10
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: 4
            spacing: 4
            Text {
                text: root.entryLabel
                color: Theme.textColor
                font.pixelSize: Theme.bodyPixel
                font.bold: true
                width: root.width - 20
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            Text {
                text: root.entryName
                color: Theme.secondaryTextColor
                font.pixelSize: Theme.smallPixel
                width: root.width - 20
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
                visible: root.entryName !== ""
            }
        }
    }

    background: Rectangle {
        radius: Theme.cardRadius
        color: root.selected ? Theme.accentColor : root.hovered ? Theme.surfaceHoverColor : Theme.surfaceColor
        border.color: root.selected ? Theme.accentColor : Theme.cardBorderColor
        border.width: 2
        Behavior on color { ColorAnimation { duration: Theme.animDuration } }
    }

    scale: pressed ? 0.97 : 1.0
    Behavior on scale { NumberAnimation { duration: 120 } }
}