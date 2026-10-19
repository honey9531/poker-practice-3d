import QtQuick
import QtQuick.Layouts

// One player at the table: hole cards above a nameplate with avatar, name,
// stack and the latest action. ``unit`` scales everything with the table.
Item {
    id: root

    property real unit: 80
    property string name
    property int stack: 0
    property var cards: []
    property bool inHand: true
    property bool folded: false
    property bool allIn: false
    property bool busted: false
    property bool isHuman: false
    property bool toAct: false
    property string lastAction: ""
    property bool isWinner: false
    property int wonAmount: 0
    property string handLabel: ""
    property var bestCards: []
    property string playerStyle: ""
    property bool animated: true
    // Deal animation: only right after a new hand starts.
    property bool animateDeal: false
    property point dealOrigin: Qt.point(0, 0)  // table centre in this item's coordinates
    property int dealOrder: 0  // position in the dealing order

    readonly property real plateWidth: unit * (isHuman ? 2.3 : 1.95)
    readonly property real plateHeight: unit * 0.62
    readonly property real cardWidth: unit * (isHuman ? 1.0 : 0.56)
    // Fraction of the cards' height visible above the nameplate.
    readonly property real cardsExposed: isHuman ? 0.84 : 0.62

    width: plateWidth
    height: plate.height + cardsRow.height * cardsExposed
    opacity: busted ? 0.35 : (folded ? 0.6 : 1)
    Behavior on opacity { enabled: root.animated; NumberAnimation { duration: Theme.durationNormal } }

    // Hole cards, tucked behind the top of the nameplate.
    Item {
        id: cardsRow
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.cardWidth * 1.7
        height: root.cardWidth * 88 / 63
        y: 0
        visible: root.cards.length > 0
        // Fixed two positions: delegates live as long as the seat, so revealing
        // cards flips them in place instead of recreating (and re-dealing) them.
        Repeater {
            model: 2
            PlayingCard {
                id: holeCard
                readonly property bool present: index < root.cards.length
                readonly property string code: present ? root.cards[index] : ""
                // Face down until it has landed in front of the player.
                property bool landed: true
                visible: present
                x: index * root.cardWidth * 0.7
                width: root.cardWidth
                height: width * aspect
                rotation: (index - 0.5) * 7
                card: code
                faceUp: code !== "" && landed
                highlighted: code !== "" && root.bestCards.indexOf(code) >= 0
                animated: root.animated

                Timer {
                    id: landTimer
                    onTriggered: holeCard.landed = true
                }
                function deal() {
                    if (!present || !root.animateDeal) {
                        landed = true
                        return
                    }
                    const delay = (index * 6 + root.dealOrder) * 60
                    landed = false
                    dealFrom(root.dealOrigin.x - x - cardsRow.x, root.dealOrigin.y - cardsRow.y, delay)
                    landTimer.interval = delay + 420
                    landTimer.restart()
                }
                onPresentChanged: deal()
                Component.onCompleted: deal()
            }
        }
    }

    // Turn glow.
    Rectangle {
        anchors.fill: plate
        anchors.margins: -root.unit * 0.05
        radius: plate.radius + root.unit * 0.05
        color: "transparent"
        border.color: root.isWinner ? Theme.goldBright : Theme.gold
        border.width: Math.max(2, root.unit * 0.035)
        opacity: root.toAct || root.isWinner ? 1 : 0
        Behavior on opacity { enabled: root.animated; NumberAnimation { duration: Theme.durationNormal } }

        SequentialAnimation on opacity {
            running: root.toAct && root.animated
            loops: Animation.Infinite
            NumberAnimation { from: 1; to: 0.45; duration: 700; easing.type: Easing.InOutSine }
            NumberAnimation { from: 0.45; to: 1; duration: 700; easing.type: Easing.InOutSine }
        }
    }

    Rectangle {
        id: plate
        objectName: "nameplate"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        width: root.plateWidth
        height: root.plateHeight
        radius: height * 0.22
        border.width: 1
        border.color: root.toAct ? Theme.gold : Theme.panelBorder
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#262320" }
            GradientStop { position: 1.0; color: "#141210" }
        }

        // Avatar with the player's initial.
        Rectangle {
            id: avatar
            x: plate.height * 0.12
            anchors.verticalCenter: parent.verticalCenter
            width: plate.height * 0.76
            height: width
            radius: width / 2
            color: root.isHuman ? "#2a4a39" : "#33302c"
            border.width: Math.max(1.5, width * 0.06)
            border.color: root.isHuman ? Theme.gold
                        : root.playerStyle === "Aggressive" ? Theme.accentRed
                        : root.playerStyle === "Conservative" ? "#5a7fa8"
                        : Theme.goldDim

            Text {
                anchors.centerIn: parent
                text: root.name.length > 0 ? root.name[0].toUpperCase() : "?"
                font.family: Theme.fontDisplay
                font.pixelSize: parent.height * 0.5
                color: Theme.textPrimary
            }
        }

        ColumnLayout {
            anchors {
                left: avatar.right; leftMargin: plate.height * 0.16
                right: parent.right; rightMargin: plate.height * 0.16
                verticalCenter: parent.verticalCenter
            }
            spacing: 0

            Text {
                objectName: "seatName"
                Layout.fillWidth: true
                text: root.name
                elide: Text.ElideRight
                font.family: Theme.fontBody
                font.pixelSize: Math.max(10, root.unit * 0.16)
                color: Theme.textSecondary
            }
            Text {
                objectName: "seatStack"
                Layout.fillWidth: true
                text: root.busted ? "Out" : Theme.formatChips(root.stack)
                elide: Text.ElideRight
                font.family: Theme.fontBody
                font.pixelSize: Math.max(11, root.unit * 0.2)
                font.bold: true
                color: root.allIn ? Theme.actionAllIn : Theme.goldBright
            }
        }
    }

    // Status pill under the nameplate: last action, all-in, or winnings.
    Rectangle {
        id: pill
        objectName: "statusPill"
        readonly property string label: root.isWinner ? "Wins " + Theme.formatChips(root.wonAmount)
                                       : root.allIn ? "All-in"
                                       : root.folded ? "Fold"
                                       : root.lastAction
        anchors.horizontalCenter: plate.horizontalCenter
        anchors.top: plate.bottom
        anchors.topMargin: root.unit * 0.05
        visible: label !== ""
        width: pillText.implicitWidth + root.unit * 0.24
        height: pillText.implicitHeight + root.unit * 0.06
        radius: height / 2
        color: root.isWinner ? Theme.gold : "#1b1917"
        border.width: 1
        border.color: root.isWinner ? Theme.goldBright : Qt.darker(Theme.actionColor(label), 1.6)

        Text {
            id: pillText
            anchors.centerIn: parent
            text: pill.label.toUpperCase()
            font.family: Theme.fontBody
            font.pixelSize: Math.max(9, root.unit * 0.13)
            font.bold: true
            font.letterSpacing: 0.8
            color: root.isWinner ? Theme.background : Theme.actionColor(pill.label)
        }
    }

    // Showdown hand description.
    Text {
        anchors.horizontalCenter: plate.horizontalCenter
        anchors.top: pill.visible ? pill.bottom : plate.bottom
        anchors.topMargin: root.unit * 0.04
        visible: root.handLabel !== ""
        text: root.handLabel
        font.family: Theme.fontBody
        font.pixelSize: Math.max(9, root.unit * 0.13)
        font.italic: true
        color: root.isWinner ? Theme.goldBright : Theme.textSecondary
        style: Text.Outline
        styleColor: "#80000000"
    }
}
