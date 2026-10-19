import QtQuick
import QtQuick.Layouts
import PokerPractice.Bridge
import "../components"

// Choose session options before sitting down.
ScreenScaffold {
    id: root
    title: "New Session"

    // Initial values (e.g. from saved settings).
    property var defaults: ({})

    signal startRequested(var config)

    property int opponents: defaults.opponents !== undefined ? defaults.opponents : 3
    property int startingStack: defaults.startingStack !== undefined ? defaults.startingStack : 2000
    property int bigBlind: defaults.bigBlind !== undefined ? defaults.bigBlind : 20
    property string opponentStyle: defaults.opponentStyle !== undefined ? defaults.opponentStyle : "mixed"
    property string difficulty: defaults.difficulty !== undefined ? defaults.difficulty : "normal"
    property int blindIncreaseEvery: defaults.blindIncreaseEvery !== undefined ? defaults.blindIncreaseEvery : 0

    function config() {
        return {
            opponents: opponents,
            startingStack: startingStack,
            smallBlind: bigBlind / 2,
            bigBlind: bigBlind,
            opponentStyle: opponentStyle,
            difficulty: difficulty,
            blindIncreaseEvery: blindIncreaseEvery
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.background
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(parent.width - 2 * Theme.spacingLarge, 640)
        height: form.implicitHeight + 2 * Theme.spacingLarge + 8
        radius: Theme.radius * 2
        color: Theme.panel
        border.width: 1
        border.color: Theme.panelBorder

        ColumnLayout {
            id: form
            anchors.fill: parent
            anchors.margins: Theme.spacingLarge
            spacing: Theme.spacingLarge

            Text {
                text: "Table setup"
                font.family: Theme.fontDisplay
                font.pixelSize: Theme.fontSizeLarge + 4
                color: Theme.textPrimary
            }

            GridLayout {
                columns: 2
                columnSpacing: Theme.spacingLarge
                rowSpacing: Theme.spacing + 4

                FieldLabel { text: "Opponents" }
                SegmentedSelector {
                    objectName: "opponentsSelector"
                    options: [1, 2, 3, 4, 5].map(n => ({ label: String(n), value: n }))
                    value: root.opponents
                    onActivated: v => root.opponents = v
                }

                FieldLabel { text: "Starting stack" }
                SegmentedSelector {
                    objectName: "stackSelector"
                    options: [1000, 2000, 5000, 10000].map(n => ({ label: Theme.formatChips(n), value: n }))
                    value: root.startingStack
                    onActivated: v => root.startingStack = v
                }

                FieldLabel { text: "Blinds" }
                SegmentedSelector {
                    objectName: "blindsSelector"
                    options: [10, 20, 50, 100].map(n => ({ label: (n / 2) + " / " + n, value: n }))
                    value: root.bigBlind
                    onActivated: v => root.bigBlind = v
                }

                FieldLabel { text: "Blinds increase" }
                SegmentedSelector {
                    objectName: "blindIncreaseSelector"
                    options: [
                        { label: "Never", value: 0 },
                        { label: "Every 5 hands", value: 5 },
                        { label: "Every 10", value: 10 },
                        { label: "Every 20", value: 20 }
                    ]
                    value: root.blindIncreaseEvery
                    onActivated: v => root.blindIncreaseEvery = v
                }

                FieldLabel { text: "Opponent style" }
                SegmentedSelector {
                    objectName: "styleSelector"
                    options: [
                        { label: "Mixed", value: "mixed" },
                        { label: "Conservative", value: "conservative" },
                        { label: "Balanced", value: "balanced" },
                        { label: "Aggressive", value: "aggressive" }
                    ]
                    value: root.opponentStyle
                    onActivated: v => root.opponentStyle = v
                }

                FieldLabel { text: "Difficulty" }
                SegmentedSelector {
                    objectName: "difficultySelector"
                    options: [
                        { label: "Easy", value: "easy" },
                        { label: "Normal", value: "normal" },
                        { label: "Hard", value: "hard" }
                    ]
                    value: root.difficulty
                    onActivated: v => root.difficulty = v
                }

                FieldLabel { text: "Hand analysis" }
                SegmentedSelector {
                    objectName: "analysisSelector"
                    options: [{ label: "Off", value: false }, { label: "After each hand", value: true }]
                    value: Settings.analysisMode
                    onActivated: v => Settings.analysisMode = v
                }
            }

            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Starting stack is " + Math.round(root.startingStack / root.bigBlind) + " big blinds. "
                      + (root.blindIncreaseEvery > 0
                         ? "Blinds rise every " + root.blindIncreaseEvery + " hands: "
                           + Game.blindPreview(root.bigBlind / 2, root.bigBlind, 5).join(" \u2192 ") + " \u2192 \u2026 "
                         : "Blinds stay the same all session. ")
                      + "Chips are virtual and have no monetary value."
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.textMuted
            }

            MenuButton {
                objectName: "startSessionButton"
                Layout.alignment: Qt.AlignRight
                text: "Start Session"
                primary: true
                onClicked: root.startRequested(root.config())
            }
        }
    }

    component FieldLabel: Text {
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody
        color: Theme.textSecondary
    }
}
