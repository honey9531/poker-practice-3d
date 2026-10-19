import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Betting controls for the human player.
//
// ``actions`` is the legal-action map published by the Game bridge (empty when
// it is not the human's turn). Every submission carries ``actions.step`` so the
// engine can reject stale or duplicate actions; the panel also locks itself
// after a click until a new decision point (``actions.key``: hand and step)
// arrives.
Rectangle {
    id: root

    property var actions: ({})
    property int totalPot: 0
    property int bigBlind: 0
    property string waitingText: ""

    signal actionRequested(string kind, int amount, int step)

    readonly property bool active: actions.step !== undefined
    property string submittedKey: ""
    readonly property bool ready: active && submittedKey !== actions.key
    readonly property bool canSize: ready && (actions.canBet || actions.canRaise)
    property int raiseTo: 0

    implicitHeight: 118
    color: Theme.backgroundRaised

    onActionsChanged: resetAmount()
    Component.onCompleted: resetAmount()

    // Reads ``actions`` directly: this runs before bindings such as ``active``
    // have been re-evaluated for the new value.
    function resetAmount() {
        if (actions.step !== undefined)
            raiseTo = actions.minTo
    }

    function clampAmount(value) {
        if (!canSize)
            return value
        return Math.max(actions.minTo, Math.min(actions.maxTo, Math.round(value)))
    }

    // Snap slider values to big-blind multiples, but always allow min and max.
    function snapped(value) {
        if (!canSize)
            return 0
        if (value >= actions.maxTo)
            return actions.maxTo
        const step = Math.max(1, bigBlind)
        return clampAmount(Math.round(value / step) * step)
    }

    function submit(kind, amount) {
        if (!ready)
            return
        submittedKey = actions.key
        actionRequested(kind, amount || 0, actions.step)
    }

    // Folding when checking is free needs a second click (or F press).
    property bool confirmingFold: false
    Timer { id: foldConfirmTimer; interval: 2500; onTriggered: root.confirmingFold = false }
    onReadyChanged: confirmingFold = false

    function fold() {
        if (!ready || !actions.canFold)
            return
        if (actions.canCheck && !confirmingFold) {
            confirmingFold = true
            foldConfirmTimer.restart()
            return
        }
        confirmingFold = false
        submit("fold")
    }
    function checkOrCall() {
        if (!ready)
            return
        if (actions.canCheck)
            submit("check")
        else if (actions.canCall)
            submit("call")
    }
    function betOrRaise() {
        if (canSize)
            submit(actions.canBet ? "bet" : "raise", raiseTo)
    }
    function allIn() { if (ready && actions.canAllIn) submit("all_in") }

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1
        color: Theme.divider
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingLarge
        anchors.rightMargin: Theme.spacingLarge
        anchors.topMargin: Theme.spacing
        anchors.bottomMargin: Theme.spacing
        spacing: Theme.spacingLarge

        // Situation summary.
        GridLayout {
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: 170
            columns: 2
            rowSpacing: 2
            columnSpacing: Theme.spacing

            InfoLabel { text: "To call" }
            InfoValue {
                objectName: "toCallValue"
                text: root.active ? Theme.formatChips(root.actions.callAmount) : "—"
                highlight: root.active && root.actions.callAmount > 0
            }
            InfoLabel { text: "Pot" }
            InfoValue { objectName: "potValue"; text: Theme.formatChips(root.totalPot) }
            InfoLabel { text: "Stack" }
            InfoValue { text: root.active ? Theme.formatChips(root.actions.stack) : "—" }
            InfoLabel { text: root.active && root.actions.canRaise ? "Min raise" : "Min bet" }
            InfoValue { text: root.canSize ? Theme.formatChips(root.actions.minTo) : "—" }
        }

        Item { Layout.fillWidth: true }

        ColumnLayout {
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            spacing: Theme.spacing

            // Bet sizing: presets, slider and exact amount.
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 6
                opacity: root.canSize ? 1 : 0.35
                enabled: root.canSize

                Repeater {
                    model: root.active ? (root.actions.presets || []).filter(p => p.label !== "All-in") : []
                    Button {
                        objectName: "preset_" + modelData.label
                        implicitHeight: 28
                        implicitWidth: Math.max(52, presetLabel.implicitWidth + 16)
                        hoverEnabled: true
                        onClicked: root.raiseTo = root.clampAmount(modelData.amount)
                        contentItem: Text {
                            id: presetLabel
                            text: modelData.label
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.family: Theme.fontBody
                            font.pixelSize: 12
                            color: parent.hovered ? Theme.goldBright : Theme.textSecondary
                        }
                        background: Rectangle {
                            radius: 4
                            color: root.raiseTo === modelData.amount ? "#3a3326" : Theme.panel
                            border.width: 1
                            border.color: root.raiseTo === modelData.amount ? Theme.goldDim : Theme.panelBorder
                        }
                    }
                }

                Slider {
                    id: slider
                    objectName: "betSlider"
                    Layout.preferredWidth: 170
                    from: root.canSize ? root.actions.minTo : 0
                    to: root.canSize ? root.actions.maxTo : 1
                    value: root.raiseTo
                    onMoved: root.raiseTo = root.snapped(value)

                    background: Rectangle {
                        x: slider.leftPadding
                        y: slider.topPadding + slider.availableHeight / 2 - height / 2
                        width: slider.availableWidth
                        height: 4
                        radius: 2
                        color: Theme.panelBorder
                        Rectangle {
                            width: slider.visualPosition * parent.width
                            height: parent.height
                            radius: 2
                            color: Theme.gold
                        }
                    }
                    handle: Rectangle {
                        x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                        y: slider.topPadding + slider.availableHeight / 2 - height / 2
                        width: 18
                        height: 18
                        radius: 9
                        color: slider.pressed ? Theme.goldBright : Theme.textPrimary
                        border.color: Theme.goldDim
                    }
                }

                TextField {
                    id: amountField
                    objectName: "amountField"
                    Layout.preferredWidth: 92
                    implicitHeight: 30
                    horizontalAlignment: Text.AlignRight
                    text: root.canSize ? String(root.raiseTo) : ""
                    validator: IntValidator { bottom: 0 }
                    inputMethodHints: Qt.ImhDigitsOnly
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.fontSizeBody
                    selectByMouse: true
                    onEditingFinished: {
                        root.raiseTo = root.clampAmount(parseInt(text || "0"))
                        text = String(root.raiseTo)
                    }
                    Keys.onReturnPressed: { editingFinished(); root.betOrRaise() }
                    background: Rectangle {
                        radius: 4
                        color: Theme.background
                        border.width: 1
                        border.color: amountField.activeFocus ? Theme.gold : Theme.panelBorder
                    }
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8

                ActionButton {
                    objectName: "foldButton"
                    text: root.confirmingFold ? "Fold anyway?" : "Fold"
                    shortcutHint: "F"
                    variant: "fold"
                    enabled: root.ready && root.actions.canFold
                    onClicked: root.fold()
                }
                ActionButton {
                    objectName: "checkCallButton"
                    text: !root.active ? "Check"
                        : root.actions.canCheck ? "Check"
                        : root.actions.callAmount >= root.actions.stack ? "Call all-in " + Theme.formatChips(root.actions.callAmount)
                        : "Call " + Theme.formatChips(root.actions.callAmount)
                    shortcutHint: "C"
                    enabled: root.ready && (root.actions.canCheck || root.actions.canCall)
                    onClicked: root.checkOrCall()
                }
                ActionButton {
                    objectName: "betRaiseButton"
                    text: !root.canSize ? "Raise"
                        : (root.actions.canBet ? "Bet " : "Raise to ") + Theme.formatChips(root.raiseTo)
                    shortcutHint: "R"
                    variant: "primary"
                    enabled: root.canSize
                    onClicked: root.betOrRaise()
                }
                ActionButton {
                    objectName: "allInButton"
                    text: "All-in"
                    shortcutHint: "A"
                    variant: "allin"
                    enabled: root.ready && root.actions.canAllIn
                    onClicked: root.allIn()
                }
            }
        }
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: Theme.spacingLarge + 200
        anchors.verticalCenter: parent.verticalCenter
        visible: !root.active && root.waitingText !== ""
        text: root.waitingText
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody
        font.italic: true
        color: Theme.textMuted
    }

    component InfoLabel: Text {
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeSmall
        color: Theme.textMuted
    }
    component InfoValue: Text {
        property bool highlight: false
        Layout.alignment: Qt.AlignRight
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody
        font.bold: true
        color: highlight ? Theme.goldBright : Theme.textPrimary
    }
}
