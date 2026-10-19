import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import PokerPractice.Bridge
import "../components"

// Developer gallery of cards and chips (Ctrl+Shift+G). Not part of normal navigation.
ScreenScaffold {
    id: root
    title: "Component Gallery"

    readonly property var ranks: ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
    readonly property var suits: ["s", "h", "d", "c"]

    Rectangle {
        anchors.fill: parent
        color: Theme.felt
    }

    Flickable {
        id: flick
        objectName: "galleryFlick"
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight + 2 * Theme.spacingLarge
        clip: true
        ScrollBar.vertical: ScrollBar {}

        ColumnLayout {
            id: content
            x: Theme.spacingLarge
            y: Theme.spacingLarge
            width: flick.width - 2 * Theme.spacingLarge
            spacing: Theme.spacingLarge

            // Card width that fits 13 cards per row.
            readonly property real cardWidth: Math.min(96, (width - 12 * 8) / 13)

            SectionLabel { text: "Deck" }
            Repeater {
                model: root.suits
                Row {
                    spacing: 8
                    property string suit: modelData
                    Repeater {
                        model: root.ranks
                        PlayingCard {
                            width: content.cardWidth
                            height: width * aspect
                            card: modelData + parent.suit
                            animated: false
                        }
                    }
                }
            }

            SectionLabel { text: "States: face down, unknown, highlighted, dimmed, small, large" }
            Row {
                spacing: 18
                PlayingCard { width: 90; height: width * aspect; card: "Ah"; faceUp: false; animated: false }
                PlayingCard { width: 90; height: width * aspect; card: ""; animated: false }
                PlayingCard { width: 90; height: width * aspect; card: "Qs"; highlighted: true; animated: false }
                PlayingCard { width: 90; height: width * aspect; card: "7d"; dimmed: true; animated: false }
                PlayingCard { width: 44; height: width * aspect; card: "Tc"; animated: false; anchors.bottom: parent.bottom }
                PlayingCard { width: 180; height: width * aspect; card: "Kh"; animated: false }
                PlayingCard {
                    // Distorted box: the card keeps its proportions.
                    width: 160; height: 120; card: "Jd"; animated: false
                    Rectangle { anchors.fill: parent; color: "transparent"; border.color: Theme.goldDim }
                }
            }

            SectionLabel { text: "Chips: denominations at 72, 40 and 24 px" }
            Repeater {
                model: [72, 40, 24]
                Row {
                    spacing: 14
                    property real chipSize: modelData
                    Repeater {
                        model: Chips.denominations
                        PokerChip {
                            width: parent.chipSize
                            baseColor: modelData.color
                            insertColor: modelData.insert
                            textColor: modelData.text
                            label: modelData.label
                        }
                    }
                }
            }

            SectionLabel { text: "Stacks" }
            Row {
                spacing: 22
                Repeater {
                    model: Chips.denominations
                    ChipStack {
                        anchors.bottom: parent.bottom
                        chipWidth: 52
                        count: index * 2 + 1
                        baseColor: modelData.color
                        insertColor: modelData.insert
                        textColor: modelData.text
                        label: modelData.label
                    }
                }
            }

            SectionLabel { text: "Piles: 35, 480, 1 275, 23 480, 250 000" }
            Row {
                spacing: 40
                Repeater {
                    model: [35, 480, 1275, 23480, 250000]
                    Column {
                        anchors.bottom: parent.bottom
                        spacing: 6
                        ChipPile { amount: modelData; chipWidth: 36; anchors.horizontalCenter: parent.horizontalCenter }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.toLocaleString(Qt.locale("en_US"), "f", 0)
                            color: Theme.textPrimary
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.fontSizeBody
                        }
                    }
                }
            }
        }
    }

    component SectionLabel: Text {
        color: Theme.goldBright
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeSmall
        font.letterSpacing: 1.5
        font.capitalization: Font.AllUppercase
    }
}
