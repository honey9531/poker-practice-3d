import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import PokerPractice.Bridge
import "../components"

ScreenScaffold {
    id: root
    title: "Settings"

    readonly property var onOff: [{ label: "Off", value: false }, { label: "On", value: true }]

    Flickable {
        anchors.fill: parent
        contentHeight: card.height + 2 * Theme.spacingLarge
        clip: true
        ScrollBar.vertical: ScrollBar {}

        Rectangle {
            id: card
            x: (parent.width - width) / 2
            y: Theme.spacingLarge
            width: Math.min(parent.width - 2 * Theme.spacingLarge, 680)
            height: form.implicitHeight + 2 * Theme.spacingLarge
            radius: Theme.radius * 2
            color: Theme.panel
            border.width: 1
            border.color: Theme.panelBorder

            ColumnLayout {
                id: form
                anchors.fill: parent
                anchors.margins: Theme.spacingLarge
                spacing: Theme.spacingLarge

                SectionTitle { text: "Gameplay" }
                GridLayout {
                    columns: 2
                    columnSpacing: Theme.spacingLarge
                    rowSpacing: Theme.spacing + 4

                    Label2 { text: "Animations" }
                    SegmentedSelector {
                        objectName: "animationsSelector"
                        options: root.onOff
                        value: Settings.animationsEnabled
                        onActivated: v => Settings.animationsEnabled = v
                    }
                    Label2 { text: "Deal next hand automatically" }
                    SegmentedSelector {
                        objectName: "autoDealSelector"
                        options: root.onOff
                        value: Settings.autoDeal
                        onActivated: v => Settings.autoDeal = v
                    }
                    Label2 { text: "Hand analysis after each hand" }
                    SegmentedSelector {
                        objectName: "analysisSettingSelector"
                        options: root.onOff
                        value: Settings.analysisMode
                        onActivated: v => Settings.analysisMode = v
                    }
                }

                SectionTitle { text: "Appearance" }
                GridLayout {
                    columns: 2
                    columnSpacing: Theme.spacingLarge
                    rowSpacing: Theme.spacing + 4

                    Label2 { text: "Chip colours" }
                    SegmentedSelector {
                        objectName: "chipSchemeSelector"
                        options: Settings.chipSchemes.map(n => ({ label: n.charAt(0).toUpperCase() + n.slice(1), value: n }))
                        value: Settings.chipScheme
                        onActivated: v => Settings.chipScheme = v
                    }
                }
                Row {
                    spacing: 10
                    Repeater {
                        model: Chips.denominations
                        PokerChip {
                            width: 42
                            baseColor: modelData.color
                            insertColor: modelData.insert
                            textColor: modelData.text
                            label: modelData.label
                        }
                    }
                }

                SectionTitle { text: "Data" }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WrapAnywhere
                    text: "Hand history, statistics and settings are stored in:\n" + App.dataDirectory
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.fontSizeSmall
                    color: Theme.textSecondary
                }
                ToolbarButton {
                    objectName: "clearHistoryButton"
                    text: "Delete hand history and statistics…"
                    onClicked: clearDialog.open()
                }

                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "Changes are saved immediately. Virtual chips only — no real-money gambling."
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.fontSizeSmall
                    color: Theme.textMuted
                }
            }
        }
    }

    ConfirmDialog {
        id: clearDialog
        title: "Delete hand history?"
        text: "This permanently deletes every recorded session, hand and statistic. Settings are kept."
        confirmText: "Delete"
        onConfirmed: {
            Stats.resetAll()
            History.refresh()
        }
    }

    component SectionTitle: Text {
        font.family: Theme.fontDisplay
        font.pixelSize: Theme.fontSizeLarge
        color: Theme.textPrimary
    }
    component Label2: Text {
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody
        color: Theme.textSecondary
    }
}
