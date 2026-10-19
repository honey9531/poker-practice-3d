import QtQuick
import PokerPractice.Bridge

// An amount shown as stacks of chips, largest denomination on the left.
// Display only: ``amount`` comes from the engine and is never modified here.
Item {
    id: root

    property int amount: 0
    property real chipWidth: 34
    property int maxPerStack: 10
    property int maxStacks: 6
    property bool animated: true

    // [{value, label, color, insert, text, count}] split into display stacks.
    readonly property var stacks: {
        Chips.denominations  // re-evaluate when the colour scheme changes
        const result = []
        for (const entry of Chips.breakdown(amount)) {
            let remaining = entry.count
            while (remaining > 0 && result.length < maxStacks) {
                const n = Math.min(remaining, maxPerStack)
                result.push(Object.assign({}, entry, { count: n }))
                remaining -= n
            }
        }
        return result
    }

    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight
    width: implicitWidth
    height: implicitHeight

    // Slide in from (dx, dy) relative to the final position.
    function animateFrom(dx, dy, delay) {
        motion.stop()
        offset.x = dx
        offset.y = dy
        if (!animated) {
            offset.x = 0
            offset.y = 0
            return
        }
        pause.duration = delay || 0
        motion.start()
    }

    transform: Translate { id: offset }

    SequentialAnimation {
        id: motion
        PauseAnimation { id: pause }
        ParallelAnimation {
            NumberAnimation { target: offset; property: "x"; to: 0; duration: 420; easing.type: Easing.OutCubic }
            NumberAnimation { target: offset; property: "y"; to: 0; duration: 420; easing.type: Easing.OutCubic }
        }
    }

    Row {
        id: row
        spacing: root.chipWidth * 0.08
        Repeater {
            model: root.stacks
            ChipStack {
                anchors.bottom: parent.bottom
                chipWidth: root.chipWidth
                count: modelData.count
                baseColor: modelData.color
                insertColor: modelData.insert
                textColor: modelData.text
                label: modelData.label
            }
        }
    }
}
