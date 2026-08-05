pragma Singleton
import QtQuick

QtObject {
    readonly property color backgroundColor: "#1e1e1e"
    readonly property color surfaceColor: "#2d2d2d"
    readonly property color surfaceHoverColor: "#383838"
    readonly property color accentColor: "#448aff"
    readonly property color accentDarker: "#2962ff"
    readonly property color textColor: "#ffffff"
    readonly property color secondaryTextColor: "#9f9f9f"
    readonly property color cardBorderColor: "#444444"
    readonly property int headingPixel: 18
    readonly property int bodyPixel: 14
    readonly property int smallPixel: 12
    readonly property int cardWidth: 160
    readonly property int cardHeight: 96
    readonly property int cardRadius: 8
    readonly property int cardSpacing: 10
    readonly property int animDuration: 180
}