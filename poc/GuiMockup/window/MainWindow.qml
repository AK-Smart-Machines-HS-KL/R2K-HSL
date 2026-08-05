import QtQuick
import Theme

Item {
    id: window
    width: 520
    height: 460

    readonly property var stepPages: [
        "../pages/ScenarioPage.qml",
        "../pages/StrategyPage.qml",
        "../pages/ModelPage.qml",
        "../pages/RelayPage.qml",
        "../pages/ExplainPage.qml",
        "../pages/HeadlessPage.qml",
        "../pages/DurationPage.qml"
    ]

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        // ── Step page via Loader ─────────────────────────────────
        Loader {
            id: pageLoader
            width: parent.width
            height: Theme.cardHeight + 60
            source: window.stepPages[Bridge.backend.current_step] || ""
            clip: true
            onStatusChanged: {
                if (status === Loader.Error) {
                    errorText.visible = true
                    errorText.text = "Failed to load: " + source
                } else {
                    errorText.visible = false
                }
            }
        }
        Text {
            id: errorText
            visible: false
            color: "red"
            font.pixelSize: Theme.bodyPixel
            anchors.horizontalCenter: parent.horizontalCenter
        }

        // ── Step nav (between page and summary) ─────────────────
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 12

            Rectangle {
                width: 40; height: 40; radius: 20
                anchors.verticalCenter: parent.verticalCenter
                color: Bridge.backend.current_step > 0
                       ? (backMa.containsMouse ? Theme.surfaceHoverColor : Theme.surfaceColor)
                       : Theme.surfaceColor
                border.color: Theme.cardBorderColor; border.width: 1
                opacity: Bridge.backend.current_step > 0 ? 1.0 : 0.4
                Text { anchors.centerIn: parent; text: "\u25C0"; color: Theme.textColor; font.pixelSize: Theme.headingPixel }
                MouseArea { id: backMa; anchors.fill: parent; hoverEnabled: true
                    enabled: Bridge.backend.current_step > 0; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: Bridge.backend.go_back() }
            }

            Repeater {
                model: Bridge.backend.step_count
                Rectangle {
                    width: 10; height: 10; radius: 5
                    color: index === Bridge.backend.current_step ? Theme.accentColor : Theme.cardBorderColor
                    anchors.verticalCenter: parent.verticalCenter
                    Behavior on color { ColorAnimation { duration: Theme.animDuration } }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.backend.go_to_step(index) }
                }
            }

            Rectangle {
                width: 40; height: 40; radius: 20
                anchors.verticalCenter: parent.verticalCenter
                color: Bridge.backend.current_step < Bridge.backend.step_count - 1
                       ? (fwdMa.containsMouse ? Theme.surfaceHoverColor : Theme.surfaceColor)
                       : Theme.surfaceColor
                border.color: Theme.cardBorderColor; border.width: 1
                opacity: Bridge.backend.current_step < Bridge.backend.step_count - 1 ? 1.0 : 0.4
                Text { anchors.centerIn: parent; text: "\u25B6"; color: Theme.textColor; font.pixelSize: Theme.headingPixel }
                MouseArea { id: fwdMa; anchors.fill: parent; hoverEnabled: true
                    enabled: Bridge.backend.current_step < Bridge.backend.step_count - 1; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: Bridge.backend.go_forward() }
            }
        }

        // ── Config summary (tabulated) ───────────────────────────
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 6
            Text { text: "Summary"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
            Grid {
                columns: 2; columnSpacing: 8; rowSpacing: 1
                Text { text: "Scenario:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.selected_scenario || "\u2014"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                Text { text: "Strategy:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.selected_strategy || "\u2014"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                Text { text: "Model:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.selected_model || "\u2014"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                Text { text: "Relay:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.selected_relay || "\u2014"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                Text { text: "Explain:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.explain_enabled ? "ON" : "OFF"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                Text { text: "Headless:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.headless_enabled ? "ON" : "OFF"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                Text { text: "Duration:"; color: Theme.secondaryTextColor; font.pixelSize: Theme.bodyPixel; width: 80 }
                Text { text: Bridge.backend.duration_seconds + "s"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
            }
        }

        Item { width: 1; height: 4 }

        // ── Action buttons ───────────────────────────────────────
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 12
            Rectangle {
                width: 120; height: 40; radius: Theme.cardRadius
                anchors.verticalCenter: parent.verticalCenter
                color: playMa.containsMouse ? Theme.accentDarker : Theme.accentColor
                opacity: Bridge.backend.selected_scenario !== ""
                         && Bridge.backend.selected_strategy !== ""
                         && Bridge.backend.selected_model !== "" ? 1.0 : 0.4
                Text { anchors.centerIn: parent; text: "Run"; color: Theme.textColor; font.pixelSize: Theme.headingPixel; font.bold: true }
                MouseArea { id: playMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    enabled: Bridge.backend.selected_scenario !== ""
                             && Bridge.backend.selected_strategy !== ""
                             && Bridge.backend.selected_model !== ""
                    onClicked: Bridge.backend.launch() }
            }
            Rectangle {
                width: 120; height: 40; radius: Theme.cardRadius
                anchors.verticalCenter: parent.verticalCenter
                color: batchMa.containsMouse ? Theme.surfaceHoverColor : Theme.surfaceColor
                border.color: Theme.cardBorderColor; border.width: 1
                opacity: Bridge.backend.selected_scenario !== ""
                         && Bridge.backend.selected_strategy !== ""
                         && Bridge.backend.selected_model !== "" ? 1.0 : 0.4
                Text { anchors.centerIn: parent; text: "Batch"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                MouseArea { id: batchMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    enabled: Bridge.backend.selected_scenario !== ""
                             && Bridge.backend.selected_strategy !== ""
                             && Bridge.backend.selected_model !== ""
                    onClicked: batchPopup.visible = !batchPopup.visible }
            }
        }
    }

    // ── Batch popup overlay (full window) ────────────────────
    Rectangle {
        id: batchPopup
        anchors.fill: parent
        visible: false
        color: "#80000000"
        z: 100

        property int count: 3

        MouseArea {
            anchors.fill: parent
            onClicked: batchPopup.visible = false
        }

        Rectangle {
            anchors.centerIn: parent
            width: 320; height: 220
            radius: Theme.cardRadius
            color: Theme.surfaceColor
            border.color: Theme.cardBorderColor; border.width: 1
            z: 1

            Column {
                anchors.centerIn: parent
                spacing: 20

                Text {
                    text: "Confirm Batch Run"
                    color: Theme.textColor
                    font.pixelSize: Theme.headingPixel
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Text {
                    text: "Launch " + batchPopup.count + " sequential run" + (batchPopup.count !== 1 ? "s" : "") + "?"
                    color: Theme.secondaryTextColor
                    font.pixelSize: Theme.bodyPixel
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8
                    Text { text: "Runs:"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel; anchors.verticalCenter: parent.verticalCenter }
                    Rectangle {
                        width: 50; height: 32; radius: Theme.cardRadius; color: Theme.backgroundColor
                        border.color: Theme.cardBorderColor; border.width: 1
                        TextInput { anchors.centerIn: parent; color: Theme.textColor; font.pixelSize: Theme.bodyPixel
                            text: batchPopup.count.toString(); horizontalAlignment: Text.AlignHCenter
                            onTextChanged: { var v = parseInt(text); if (!isNaN(v) && v > 0) batchPopup.count = v }
                            inputMethodHints: Qt.ImhDigitsOnly }
                    }
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 12
                    Rectangle {
                        width: 100; height: 36; radius: Theme.cardRadius; color: batchBackMa.containsMouse ? Theme.surfaceHoverColor : Theme.backgroundColor
                        border.color: Theme.cardBorderColor; border.width: 1
                        Text { anchors.centerIn: parent; text: "Back"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel }
                        MouseArea { id: batchBackMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: batchPopup.visible = false }
                    }
                    Rectangle {
                        width: 100; height: 36; radius: Theme.cardRadius; color: batchRunMa.containsMouse ? Theme.accentDarker : Theme.accentColor
                        Text { anchors.centerIn: parent; text: "Run"; color: Theme.textColor; font.pixelSize: Theme.bodyPixel; font.bold: true }
                        MouseArea { id: batchRunMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: { Bridge.batch.launch_batch(batchPopup.count); batchPopup.visible = false } }
                    }
                }
            }
        }
    }
}
