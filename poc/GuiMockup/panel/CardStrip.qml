import QtQuick
import QtQuick.Controls
import Theme
import "../components" as Comps

Item {
    id: root
    property var items: []
    property int visibleStart: 0
    property int visibleCount: 2
    property string selectedName: ""
    property bool showArrows: true
    property int stripSpacing: Theme.cardSpacing
    signal selected(string name)

    height: Theme.cardHeight
    readonly property int total: items.length
    readonly property int visibleEnd: Math.min(visibleStart + visibleCount, total)
    readonly property var visibleItems: items.slice(visibleStart, visibleEnd)

    Row {
        anchors.centerIn: parent
        spacing: root.stripSpacing

        Rectangle {
            visible: root.showArrows
            width: 40; height: 40; radius: 20
            anchors.verticalCenter: parent.verticalCenter
            color: root.visibleStart > 0
                   ? (leftMa.containsMouse ? Theme.surfaceHoverColor : Theme.surfaceColor)
                   : Theme.surfaceColor
            border.color: Theme.cardBorderColor; border.width: 1
            opacity: root.visibleStart > 0 ? 1.0 : 0.3
            Text { anchors.centerIn: parent; text: "\u25C0"; color: Theme.textColor; font.pixelSize: Theme.headingPixel }
            MouseArea { id: leftMa; anchors.fill: parent; hoverEnabled: true
                enabled: root.visibleStart > 0; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.visibleStart = Math.max(0, root.visibleStart - 1) }
        }

        Repeater {
            model: root.visibleItems
            Comps.ChoiceCard {
                anchors.verticalCenter: parent.verticalCenter
                entryName: modelData.name
                entryLabel: modelData.label
                selected: modelData.name === root.selectedName
                onClicked: root.selected(modelData.name)
            }
        }

        Rectangle {
            visible: root.showArrows
            width: 40; height: 40; radius: 20
            anchors.verticalCenter: parent.verticalCenter
            color: root.visibleStart + root.visibleCount < root.total
                   ? (rightMa.containsMouse ? Theme.surfaceHoverColor : Theme.surfaceColor)
                   : Theme.surfaceColor
            border.color: Theme.cardBorderColor; border.width: 1
            opacity: root.visibleStart + root.visibleCount < root.total ? 1.0 : 0.3
            Text { anchors.centerIn: parent; text: "\u25B6"; color: Theme.textColor; font.pixelSize: Theme.headingPixel }
            MouseArea { id: rightMa; anchors.fill: parent; hoverEnabled: true
                enabled: root.visibleStart + root.visibleCount < root.total; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.visibleStart = Math.min(root.total - root.visibleCount, root.visibleStart + 1) }
        }
    }
}