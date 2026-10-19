import QtQuick
import QtQuick.Layouts
import PokerPractice.Bridge
import "../components"

// The poker table. Everything shown comes from ``game``: the live Game bridge,
// or the Replay bridge (``replayMode``) for stepping through a stored hand.
Rectangle {
    id: root

    property var game: Game
    property bool replayMode: false

    // " · Level 2 · next in 4 hands" when blinds rise during the session.
    readonly property string blindSchedule: {
        if (replayMode || game.blindInterval <= 0)
            return ""
        const level = "   \u00b7   Level " + (game.blindLevel + 1)
        const left = game.handsToNextLevel
        if (left <= 0)
            return level + " \u00b7 blinds go up next hand"
        return level + " \u00b7 next in " + left + (left === 1 ? " hand" : " hands")
    }
    property bool animated: true

    signal backRequested()
    signal actionRequested(string kind, int amount, int step)
    signal dealRequested()
    signal newSessionRequested()
    signal sessionEnded()

    // True for a moment after a new hand starts, so hole cards animate only when dealt.
    property bool dealing: false
    Connections {
        target: root.game
        function onHandNumberChanged() {
            if (root.game.handNumber > 0) {
                root.dealing = root.animated
                dealWindow.restart()
            }
        }
    }
    Timer { id: dealWindow; interval: 1500; onTriggered: root.dealing = false }

    color: Theme.background

    // ---------------------------------------------------------------- top bar
    Rectangle {
        id: topBar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Theme.topBarHeight
        color: Theme.backgroundRaised
        z: 2

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacing
            anchors.rightMargin: Theme.spacing
            spacing: Theme.spacingLarge

            ToolbarButton {
                objectName: "backButton"
                text: root.replayMode ? "‹  History" : "‹  Menu"
                onClicked: root.backRequested()
            }
            Text {
                objectName: "handInfo"
                visible: root.game.handNumber > 0
                text: "Hand #" + root.game.handNumber + "   ·   Blinds "
                      + Theme.formatChips(root.game.smallBlind) + " / " + Theme.formatChips(root.game.bigBlind)
                      + root.blindSchedule
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody - 1
                color: Theme.textSecondary
            }
            Text {
                objectName: "tableMessage"
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: root.game.message
                elide: Text.ElideRight
                font.family: Theme.fontDisplay
                font.pixelSize: Theme.fontSizeLarge - 2
                color: Theme.goldBright
            }
            ToolbarButton {
                objectName: "analysisButton"
                visible: !root.replayMode && Settings.analysisMode && !root.game.handInProgress && root.game.analysis.length > 0
                text: "Analysis"
                onClicked: analysisPopup.open()
            }
            ToolbarButton {
                objectName: "endSessionButton"
                visible: !root.replayMode && root.game.sessionActive && !root.game.sessionOver
                text: "End Session"
                onClicked: endDialog.open()
            }
        }

        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1
            color: Theme.divider
        }
    }

    // ------------------------------------------------------------- table area
    Item {
        id: area
        objectName: "tableArea"
        anchors {
            left: parent.left; right: parent.right
            top: topBar.bottom; bottom: actionPanel.top
        }

        readonly property real aspect: 2.05
        readonly property real tableWidth: Math.min(width * 0.8, height * 0.7 * aspect)
        readonly property real tableHeight: tableWidth / aspect
        readonly property real tableX: (width - tableWidth) / 2
        readonly property real tableY: (height - tableHeight) / 2 - height * 0.01
        // Size unit for seats, cards and chips.
        readonly property real unit: Math.max(52, Math.min(160, tableWidth / 12))

        // Positions relative to the table rectangle, indexed by display slot
        // (0 = human at the bottom, then clockwise).
        readonly property var seatPoints: [[0.5, 1.04], [0.1, 0.82], [0.1, 0.22], [0.5, 0.03], [0.9, 0.22], [0.9, 0.82]]
        readonly property var betPoints: [[0.5, 0.69], [0.25, 0.68], [0.25, 0.32], [0.62, 0.21], [0.75, 0.32], [0.75, 0.68]]
        readonly property var markerPoints: [[0.39, 0.71], [0.18, 0.6], [0.18, 0.4], [0.39, 0.19], [0.82, 0.4], [0.82, 0.6]]

        function px(point) { return tableX + point[0] * tableWidth }
        function py(point) { return tableY + point[1] * tableHeight }
        readonly property point potPoint: Qt.point(px([0.5, 0]), py([0, 0.33]))
        readonly property point centre: Qt.point(px([0.5, 0]), py([0, 0.5]))

        // Chips travelling across the felt (bets to the pot, pots to winners).
        function flyChips(amount, from, to) {
            if (!root.animated || amount <= 0)
                return
            flyingChips.createObject(area, { amount: amount, startPoint: from, endPoint: to })
        }

        Component {
            id: flyingChips
            ChipPile {
                id: flyer
                property point startPoint
                property point endPoint
                chipWidth: area.unit * 0.32
                maxPerStack: 8
                maxStacks: 4
                animated: false
                z: 5
                x: startPoint.x - width / 2
                y: startPoint.y - height / 2
                ParallelAnimation {
                    running: true
                    NumberAnimation { target: flyer; property: "x"; to: flyer.endPoint.x - flyer.width / 2; duration: 480; easing.type: Easing.InOutCubic }
                    NumberAnimation { target: flyer; property: "y"; to: flyer.endPoint.y - flyer.height / 2; duration: 480; easing.type: Easing.InOutCubic }
                    SequentialAnimation {
                        PauseAnimation { duration: 380 }
                        NumberAnimation { target: flyer; property: "opacity"; to: 0; duration: 100 }
                    }
                    onFinished: flyer.destroy()
                }
            }
        }

        // Once a hand is over, clicking anywhere on the table deals the next one.
        MouseArea {
            objectName: "dealArea"
            anchors.fill: parent
            enabled: !root.replayMode && root.game.canDeal
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.dealRequested()
        }

        PokerTable {
            id: table
            objectName: "pokerTable"
            x: area.tableX
            y: area.tableY
            width: area.tableWidth
            height: area.tableHeight
        }

        PotDisplay {
            objectName: "potDisplay"
            anchors.horizontalCenter: parent.horizontalCenter
            y: area.py([0, 0.38]) - height
            pots: root.game.pots
            totalPot: root.game.totalPot
            chipWidth: area.unit * 0.36
            animated: root.animated
        }

        BoardCards {
            id: board
            objectName: "boardCards"
            cardWidth: area.unit * 0.86
            anchors.horizontalCenter: parent.horizontalCenter
            y: area.py([0, 0.5]) - height / 2
            cards: root.game.board
            highlightCards: root.game.winningCards
            animated: root.animated
        }

        // Bets and position markers, one set per seat.
        Repeater {
            model: root.game.players
            Item {
                id: furniture
                required property int slot
                required property int bet
                required property bool isDealer
                required property bool isSmallBlind
                required property bool isBigBlind
                anchors.fill: parent

                BetDisplay {
                    id: betDisplay
                    objectName: "bet" + furniture.slot
                    readonly property point point: Qt.point(area.px(area.betPoints[furniture.slot]),
                                                            area.py(area.betPoints[furniture.slot]))
                    readonly property point seatPoint: Qt.point(area.px(area.seatPoints[furniture.slot]),
                                                                area.py(area.seatPoints[furniture.slot]))
                    property int previous: 0
                    amount: furniture.bet
                    chipWidth: area.unit * 0.32
                    animated: root.animated
                    x: point.x - width / 2
                    y: point.y - height / 2

                    onAmountChanged: {
                        if (amount > previous && previous === 0)
                            pile.animateFrom(seatPoint.x - point.x, seatPoint.y - point.y, 0)
                        else if (amount < previous)
                            area.flyChips(previous - amount, point, area.potPoint)
                        previous = amount
                    }
                    Component.onCompleted: previous = amount
                }
                Row {
                    spacing: 3
                    x: area.px(area.markerPoints[furniture.slot]) - width / 2
                    y: area.py(area.markerPoints[furniture.slot]) - height / 2
                    PositionMarker { kind: "D"; size: area.unit * 0.32; visible: furniture.isDealer }
                    PositionMarker { kind: "SB"; size: area.unit * 0.28; visible: furniture.isSmallBlind }
                    PositionMarker { kind: "BB"; size: area.unit * 0.28; visible: furniture.isBigBlind }
                }
            }
        }

        Repeater {
            objectName: "seatRepeater"
            model: root.game.players
            PlayerSeat {
                // Existing PlayerSeat properties filled from model roles.
                required name
                required stack
                required cards
                required folded
                required allIn
                required busted
                required isHuman
                required toAct
                required lastAction
                required isWinner
                required wonAmount
                required handLabel
                required bestCards
                required property int slot
                required property string style

                id: seatItem
                objectName: "seat" + slot
                unit: area.unit
                playerStyle: style
                animated: root.animated
                animateDeal: root.dealing
                dealOrder: slot
                dealOrigin: Qt.point(area.centre.x - x, area.centre.y - y)

                property int previousWon: 0
                onWonAmountChanged: {
                    if (wonAmount > previousWon)
                        area.flyChips(wonAmount - previousWon, area.potPoint,
                                      Qt.point(x + width / 2, y + height - plateHeight / 2))
                    previousWon = wonAmount
                }
                // Centre the nameplate on the slot point.
                x: area.px(area.seatPoints[slot]) - width / 2
                y: area.py(area.seatPoints[slot]) - (height - plateHeight / 2)
                z: isHuman ? 2 : 1
            }
        }

        // Hand result on the felt, with the hint to deal the next hand. It sits
        // where the pot was (the pot has been paid out once the hand is over).
        Rectangle {
            objectName: "resultBanner"
            anchors.horizontalCenter: parent.horizontalCenter
            y: board.y - height - area.unit * 0.12
            visible: root.game.sessionActive && !root.game.handInProgress && root.game.handNumber > 0 && root.game.message !== ""
            width: Math.min(area.tableWidth * 0.7, Math.max(resultText.implicitWidth, dealHint.implicitWidth) + 40)
            height: bannerColumn.implicitHeight + 14
            radius: Math.min(height / 2, 22)
            color: "#cc0d0c0b"
            border.width: 1
            border.color: Theme.goldDim

            Column {
                id: bannerColumn
                anchors.centerIn: parent
                spacing: 2

                Text {
                    id: resultText
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(implicitWidth, area.tableWidth * 0.7 - 24)
                    elide: Text.ElideRight
                    text: root.game.message
                    font.family: Theme.fontDisplay
                    font.pixelSize: Math.max(13, area.unit * 0.2)
                    color: Theme.goldBright
                }
                Text {
                    id: dealHint
                    objectName: "dealHint"
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: !root.replayMode && root.game.canDeal
                    text: "Click the table to deal the next hand"
                    font.family: Theme.fontBody
                    font.pixelSize: Math.max(11, area.unit * 0.14)
                    color: Theme.textSecondary

                    SequentialAnimation on opacity {
                        running: dealHint.visible && root.animated
                        loops: Animation.Infinite
                        NumberAnimation { from: 1.0; to: 0.5; duration: 1100; easing.type: Easing.InOutSine }
                        NumberAnimation { from: 0.5; to: 1.0; duration: 1100; easing.type: Easing.InOutSine }
                    }
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: !root.game.sessionActive
            text: "No session in progress"
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeLarge
            color: Theme.textMuted
        }
    }

    ReplayControls {
        objectName: "replayControls"
        anchors.fill: actionPanel
        visible: root.replayMode
        replay: root.replayMode ? root.game : null
    }

    ActionPanel {
        id: actionPanel
        objectName: "actionPanel"
        visible: !root.replayMode
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        actions: root.game.actions
        totalPot: root.game.totalPot
        bigBlind: root.game.bigBlind
        onActionRequested: (kind, amount, step) => root.actionRequested(kind, amount, step)
    }

    AnalysisPopup {
        id: analysisPopup
        objectName: "analysisPopup"
        entries: root.game.analysis
    }

    ConfirmDialog {
        id: endDialog
        objectName: "endSessionDialog"
        title: "End this session?"
        text: root.game.handInProgress ? "The hand in progress will be abandoned. Completed hands are kept."
                                  : "You will return to the main menu."
        confirmText: "End Session"
        onConfirmed: {
            root.game.endSession()
            root.sessionEnded()
        }
    }

    // Session over: the human is out of chips or has won every chip.
    Rectangle {
        objectName: "sessionOverOverlay"
        anchors.fill: parent
        visible: root.game.sessionOver
        color: "#b0000000"
        z: 10

        MouseArea { anchors.fill: parent }  // block clicks to the table

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(460, parent.width - 48)
            height: overColumn.implicitHeight + 2 * Theme.spacingLarge
            radius: Theme.radius * 2
            color: Theme.panel
            border.width: 1
            border.color: Theme.gold

            ColumnLayout {
                id: overColumn
                anchors.fill: parent
                anchors.margins: Theme.spacingLarge
                spacing: Theme.spacing

                Text {
                    text: "Session over"
                    font.family: Theme.fontDisplay
                    font.pixelSize: Theme.fontSizeTitle - 4
                    color: Theme.textPrimary
                }
                Text {
                    Layout.fillWidth: true
                    text: root.game.message
                    wrapMode: Text.WordWrap
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.fontSizeBody
                    color: Theme.textSecondary
                }
                RowLayout {
                    Layout.alignment: Qt.AlignRight
                    Layout.topMargin: Theme.spacing
                    spacing: Theme.spacing
                    ActionButton {
                        objectName: "overMenuButton"
                        text: "Main Menu"
                        onClicked: {
                            root.game.endSession()
                            root.sessionEnded()
                        }
                    }
                    ActionButton {
                        objectName: "overNewSessionButton"
                        text: "New Session"
                        onClicked: root.newSessionRequested()
                    }
                    ActionButton {
                        objectName: "playAgainButton"
                        text: "Play Again"
                        variant: "primary"
                        onClicked: root.game.restartSession()
                    }
                }
            }
        }
    }

    // Space / Enter also deals the next hand (keyboard alternative to clicking the table).
    Shortcut { sequences: ["Space", "Return"]; enabled: root.game.canDeal; onActivated: root.dealRequested() }

    // Keyboard shortcuts for the betting actions.
    Shortcut { sequence: "F"; enabled: actionPanel.ready; onActivated: actionPanel.fold() }
    Shortcut { sequence: "C"; enabled: actionPanel.ready; onActivated: actionPanel.checkOrCall() }
    Shortcut { sequence: "R"; enabled: actionPanel.canSize; onActivated: actionPanel.betOrRaise() }
    Shortcut { sequence: "A"; enabled: actionPanel.ready; onActivated: actionPanel.allIn() }
}
