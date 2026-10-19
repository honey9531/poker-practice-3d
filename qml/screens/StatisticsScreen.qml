import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import PokerPractice.Bridge
import "../components"

ScreenScaffold {
    id: root
    title: "Statistics"

    property string scope: Stats.hasSession ? "session" : "all"
    readonly property var shown: scope === "session" ? Stats.session : Stats.allTime

    function percent(value) { return Math.round(value * 100) + "%" }
    function signedChips(value) { return (value > 0 ? "+" : "") + Theme.formatChips(value) }

    Component.onCompleted: Stats.refresh()

    Flickable {
        anchors.fill: parent
        contentHeight: column.implicitHeight + 2 * Theme.spacingLarge
        clip: true
        ScrollBar.vertical: ScrollBar {}

        ColumnLayout {
            id: column
            x: Theme.spacingLarge
            y: Theme.spacingLarge
            width: parent.width - 2 * Theme.spacingLarge
            spacing: Theme.spacingLarge

            RowLayout {
                Layout.fillWidth: true
                SegmentedSelector {
                    objectName: "scopeSelector"
                    options: [{ label: "Current session", value: "session" }, { label: "All time", value: "all" }]
                    value: root.scope
                    onActivated: v => root.scope = v
                }
                Item { Layout.fillWidth: true }
                ToolbarButton {
                    objectName: "resetStatsButton"
                    text: "Reset statistics…"
                    onClicked: resetDialog.open()
                }
            }

            Text {
                visible: root.scope === "session" && !Stats.hasSession
                text: "No session in progress. Showing nothing for the current session."
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody
                color: Theme.textMuted
            }

            GridLayout {
                objectName: "statTiles"
                Layout.fillWidth: true
                columns: Math.max(2, Math.floor(width / 230))
                columnSpacing: Theme.spacing
                rowSpacing: Theme.spacing

                StatTile {
                    objectName: "tileHands"
                    Layout.fillWidth: true
                    label: "Hands played"
                    value: Theme.formatChips(root.shown.hands)
                }
                StatTile {
                    objectName: "tileWon"
                    Layout.fillWidth: true
                    label: "Hands won"
                    value: Theme.formatChips(root.shown.handsWon)
                    detail: root.percent(root.shown.winRate) + " of hands played"
                }
                StatTile {
                    objectName: "tileNet"
                    Layout.fillWidth: true
                    label: "Net chips"
                    value: root.signedChips(root.shown.net)
                    valueColor: root.shown.net > 0 ? Theme.accentGreen : root.shown.net < 0 ? Theme.actionAllIn : Theme.textPrimary
                }
                StatTile {
                    objectName: "tileVpip"
                    Layout.fillWidth: true
                    label: "VPIP"
                    value: root.percent(root.shown.vpip)
                    detail: "Voluntarily put chips in pre-flop"
                }
                StatTile {
                    objectName: "tilePfr"
                    Layout.fillWidth: true
                    label: "Pre-flop raise"
                    value: root.percent(root.shown.pfr)
                    detail: "Raised before the flop"
                }
                StatTile {
                    objectName: "tileShowdown"
                    Layout.fillWidth: true
                    label: "Showdown frequency"
                    value: root.percent(root.shown.showdownRate)
                    detail: Theme.formatChips(root.shown.showdowns) + " showdowns"
                }
                StatTile {
                    objectName: "tileShowdownWin"
                    Layout.fillWidth: true
                    label: "Showdown win rate"
                    value: root.percent(root.shown.showdownWinRate)
                    detail: "Won at least part of the pot"
                }
                StatTile {
                    objectName: "tileBiggest"
                    Layout.fillWidth: true
                    label: "Biggest pot won"
                    value: Theme.formatChips(root.shown.biggestPot)
                }
            }

            Text {
                Layout.topMargin: Theme.spacing
                text: "Sessions"
                font.family: Theme.fontDisplay
                font.pixelSize: Theme.fontSizeLarge
                color: Theme.textPrimary
            }

            Text {
                visible: Stats.sessions.length === 0
                text: "No sessions recorded yet."
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody
                color: Theme.textMuted
            }

            Repeater {
                model: Stats.sessions
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radius
                    color: index % 2 ? "transparent" : Theme.panel

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spacing
                        anchors.rightMargin: Theme.spacing
                        spacing: Theme.spacingLarge
                        Text { Layout.preferredWidth: 150; text: modelData.startedAt; color: Theme.textSecondary; font.family: Theme.fontBody; font.pixelSize: Theme.fontSizeBody }
                        Text { Layout.preferredWidth: 140; text: modelData.opponents + " opponents · " + modelData.blinds; color: Theme.textMuted; font.family: Theme.fontBody; font.pixelSize: Theme.fontSizeSmall }
                        Text { Layout.fillWidth: true; text: Theme.formatChips(modelData.hands) + " hands"; color: Theme.textSecondary; font.family: Theme.fontBody; font.pixelSize: Theme.fontSizeBody }
                        Text {
                            text: root.signedChips(modelData.net)
                            color: modelData.net > 0 ? Theme.accentGreen : modelData.net < 0 ? Theme.actionAllIn : Theme.textSecondary
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.fontSizeBody
                            font.bold: true
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: Theme.spacing
                wrapMode: Text.WordWrap
                text: "Statistics are computed from recorded hand events for your seat. Showdown frequency is the share of hands "
                      + "you played that reached a showdown with you still in the hand."
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.textMuted
            }
        }
    }

    ConfirmDialog {
        id: resetDialog
        title: "Reset statistics?"
        text: "This permanently deletes every recorded session and hand history. Settings are kept."
        confirmText: "Delete everything"
        onConfirmed: {
            Stats.resetAll()
            History.refresh()
        }
    }
}
