import QtQuick

// Five community-card positions. Empty positions show a faint outline.
Row {
    id: root

    property var cards: []  // up to five card codes
    property var highlightCards: []
    property real cardWidth: 70
    property bool animated: true

    spacing: cardWidth * 0.12

    // Cards already on the board when the table is shown appear without animation.
    property bool ready: false
    Component.onCompleted: ready = true

    Repeater {
        model: 5
        Item {
            width: root.cardWidth
            height: width * 88 / 63

            Rectangle {
                anchors.fill: parent
                radius: width * 34 / 630
                color: Qt.rgba(0, 0, 0, 0.12)
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, 0.12)
            }

            PlayingCard {
                id: boardCard
                objectName: "boardCard" + index
                readonly property string code: index < root.cards.length ? root.cards[index] : ""
                property bool landed: true
                anchors.fill: parent
                visible: code !== ""
                card: code
                faceUp: landed
                highlighted: code !== "" && root.highlightCards.indexOf(code) >= 0
                animated: root.animated

                Timer {
                    id: flipTimer
                    onTriggered: boardCard.landed = true
                }
                // Slide in face down, then turn over (flop cards one after another).
                onCodeChanged: {
                    if (code === "" || !root.animated || !root.ready) {
                        landed = true
                        return
                    }
                    const delay = index < 3 ? index * 110 : 0
                    landed = false
                    dealFrom(0, -height * 0.7, delay)
                    flipTimer.interval = delay + 360
                    flipTimer.restart()
                }
            }
        }
    }
}
