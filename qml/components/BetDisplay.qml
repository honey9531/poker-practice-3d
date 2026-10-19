import QtQuick

// A player's current-street bet: chips on the felt plus the amount.
Item {
    id: root

    property int amount: 0
    property real chipWidth: 28
    property bool animated: true

    readonly property alias pile: chips

    width: Math.max(chips.width, label.width)
    height: chips.height + label.height + 2
    visible: amount > 0

    ChipPile {
        id: chips
        anchors.horizontalCenter: parent.horizontalCenter
        amount: root.amount
        chipWidth: root.chipWidth
        maxPerStack: 8
        maxStacks: 4
        animated: root.animated
    }

    Rectangle {
        id: label
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: chips.bottom
        anchors.topMargin: 2
        width: text.implicitWidth + 12
        height: text.implicitHeight + 2
        radius: height / 2
        color: "#99000000"

        Text {
            id: text
            anchors.centerIn: parent
            text: Theme.formatChips(root.amount)
            font.family: Theme.fontBody
            font.pixelSize: Math.max(10, root.chipWidth * 0.42)
            font.bold: true
            color: Theme.textPrimary
        }
    }
}
