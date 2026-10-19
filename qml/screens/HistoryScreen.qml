import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import PokerPractice.Bridge
import "../components"

ScreenScaffold {
    id: root
    title: "Hand History"

    signal replayRequested(int handId)

    function signedChips(value) { return (value > 0 ? "+" : "") + Theme.formatChips(value) }
    function netColor(value) { return value > 0 ? Theme.accentGreen : value < 0 ? Theme.actionAllIn : Theme.textSecondary }

    Component.onCompleted: {
        History.refresh()
        if (History.hands.length > 0 && History.detail.id === undefined)
            History.select(History.hands[0].id)
    }

    Text {
        anchors.centerIn: parent
        visible: History.hands.length === 0
        text: History.error !== "" ? History.error : "No hands recorded yet. Play a session to build your history."
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody
        color: Theme.textMuted
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLarge
        spacing: Theme.spacingLarge
        visible: History.hands.length > 0

        // ---------------------------------------------------------- hand list
        Rectangle {
            Layout.preferredWidth: Math.min(430, parent.width * 0.42)
            Layout.fillHeight: true
            radius: Theme.radius * 1.5
            color: Theme.panel
            border.width: 1
            border.color: Theme.panelBorder
            clip: true

            ListView {
                id: list
                objectName: "historyList"
                anchors.fill: parent
                anchors.margins: 4
                model: History.hands
                spacing: 2
                clip: true
                ScrollBar.vertical: ScrollBar {}

                delegate: Rectangle {
                    readonly property bool selected: History.detail.id === modelData.id
                    objectName: "historyRow" + index
                    width: ListView.view.width
                    height: 54
                    radius: Theme.radius
                    color: selected ? "#2c2a22" : (rowMouse.containsMouse ? Theme.backgroundRaised : "transparent")
                    border.width: selected ? 1 : 0
                    border.color: Theme.goldDim

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: History.select(modelData.id)
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        spacing: 10

                        Row {
                            spacing: 2
                            Repeater {
                                model: modelData.cards
                                PlayingCard { width: 26; height: width * aspect; card: modelData; animated: false }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Text {
                                text: "Hand #" + modelData.handNumber + "  ·  " + modelData.playedAt
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textMuted
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.summary
                                elide: Text.ElideRight
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeBody - 1
                                color: Theme.textSecondary
                            }
                        }
                        Text {
                            text: root.signedChips(modelData.net)
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.fontSizeBody
                            font.bold: true
                            color: root.netColor(modelData.net)
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------- detail
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radius * 1.5
            color: Theme.panel
            border.width: 1
            border.color: Theme.panelBorder
            clip: true

            Text {
                anchors.centerIn: parent
                visible: History.detail.id === undefined
                text: "Select a hand"
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody
                color: Theme.textMuted
            }

            Text {
                objectName: "detailError"
                anchors.fill: parent
                anchors.margins: Theme.spacingLarge
                visible: History.detail.error !== undefined && History.detail.error !== ""
                text: History.detail.error || ""
                wrapMode: Text.WordWrap
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody
                color: Theme.actionAllIn
            }

            Flickable {
                anchors.fill: parent
                anchors.margins: Theme.spacingLarge
                visible: History.detail.id !== undefined && !History.detail.error
                contentHeight: detail.implicitHeight
                clip: true
                ScrollBar.vertical: ScrollBar {}

                ColumnLayout {
                    id: detail
                    width: parent.width
                    spacing: Theme.spacing

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            objectName: "detailTitle"
                            Layout.fillWidth: true
                            text: History.detail.title || ""
                            elide: Text.ElideRight
                            font.family: Theme.fontDisplay
                            font.pixelSize: Theme.fontSizeLarge
                            color: Theme.textPrimary
                        }
                        SegmentedSelector {
                            objectName: "historyRevealSelector"
                            options: [{ label: "As played", value: false }, { label: "All cards", value: true }]
                            value: History.revealAll
                            onActivated: v => History.revealAll = v
                        }
                        ActionButton {
                            objectName: "replayButton"
                            variant: "primary"
                            text: "Replay"
                            onClicked: root.replayRequested(History.detail.id)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: History.detail.summary || ""
                        wrapMode: Text.WordWrap
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.fontSizeBody
                        color: Theme.goldBright
                    }

                    Row {
                        spacing: 6
                        Repeater {
                            model: History.detail.board || []
                            PlayingCard { width: 44; height: width * aspect; card: modelData; animated: false }
                        }
                    }

                    // Players with their cards and results.
                    Repeater {
                        model: History.detail.players || []
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacing
                            Row {
                                spacing: 2
                                Repeater {
                                    model: modelData.cards
                                    PlayingCard { width: 26; height: width * aspect; card: modelData; animated: false }
                                }
                            }
                            Text {
                                Layout.preferredWidth: 90
                                text: modelData.name
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeBody
                                font.bold: modelData.isHuman
                                color: Theme.textPrimary
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.style
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textMuted
                            }
                            Text {
                                text: root.signedChips(modelData.net)
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeBody
                                color: root.netColor(modelData.net)
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    // Chronological actions, with a heading at each street.
                    Repeater {
                        objectName: "detailLog"
                        model: History.detail.log || []
                        ColumnLayout {
                            readonly property bool newStreet: index === 0 || History.detail.log[index - 1].street !== modelData.street
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                visible: parent.newStreet
                                Layout.topMargin: index === 0 ? 0 : Theme.spacingSmall
                                text: modelData.street.toUpperCase()
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeSmall - 1
                                font.letterSpacing: 1.5
                                color: Theme.gold
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.text
                                wrapMode: Text.WordWrap
                                font.family: Theme.fontBody
                                font.pixelSize: Theme.fontSizeBody - 1
                                color: Theme.textSecondary
                            }
                        }
                    }
                }
            }
        }
    }
}
