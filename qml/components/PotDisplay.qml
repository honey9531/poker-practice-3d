import QtQuick

// Pot in the centre of the table: chips, total, and side-pot breakdown.
Column {
    id: root

    property var pots: []  // [{label, amount, eligible}]
    property int totalPot: 0
    property real chipWidth: 30
    property bool animated: true

    readonly property int collected: pots.reduce((sum, p) => sum + p.amount, 0)

    spacing: 4

    ChipPile {
        id: pile
        objectName: "potChips"
        anchors.horizontalCenter: parent.horizontalCenter
        amount: root.collected
        chipWidth: root.chipWidth
        maxPerStack: 10
        maxStacks: 6
        animated: root.animated
        visible: root.collected > 0
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        visible: root.totalPot > 0
        width: potText.implicitWidth + 20
        height: potText.implicitHeight + 6
        radius: height / 2
        color: "#a6000000"
        border.width: 1
        border.color: Theme.goldDim

        Text {
            id: potText
            objectName: "potTotal"
            anchors.centerIn: parent
            text: "Pot  " + Theme.formatChips(root.totalPot)
            font.family: Theme.fontBody
            font.pixelSize: Math.max(11, root.chipWidth * 0.45)
            font.bold: true
            color: Theme.goldBright
        }
    }

    // Side pots appear only when there is more than one pot.
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 8
        visible: root.pots.length > 1
        Repeater {
            model: root.pots.length > 1 ? root.pots : []
            Text {
                text: modelData.label + " " + Theme.formatChips(modelData.amount)
                font.family: Theme.fontBody
                font.pixelSize: Math.max(10, root.chipWidth * 0.36)
                color: Theme.textSecondary
                style: Text.Outline
                styleColor: "#80000000"
            }
        }
    }
}
