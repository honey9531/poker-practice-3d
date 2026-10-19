pragma Singleton
import QtQuick

// Central palette, typography and spacing for every screen.
QtObject {
    // Surfaces
    readonly property color background: "#141414"
    readonly property color backgroundRaised: "#1d1c1a"
    readonly property color panel: "#22201d"
    readonly property color panelBorder: "#3a3530"
    readonly property color divider: "#2f2b27"

    // Table
    readonly property color felt: "#0f4d32"
    readonly property color feltDark: "#0a3824"
    readonly property color feltLight: "#16613f"
    readonly property color rail: "#1b1816"
    readonly property color railHighlight: "#3a332d"
    readonly property color railEdge: "#0c0b0a"

    // Text
    readonly property color textPrimary: "#f3ede1"
    readonly property color textSecondary: "#b9b1a3"
    readonly property color textMuted: "#7d766b"

    // Accents
    readonly property color gold: "#c8a45a"
    readonly property color goldBright: "#e2c27e"
    readonly property color goldDim: "#8c7340"
    readonly property color accentRed: "#a8382f"
    readonly property color accentGreen: "#4f9a6a"

    // Typography
    readonly property string fontDisplay: "Georgia"
    readonly property string fontBody: "Segoe UI"
    readonly property int fontSizeSmall: 12
    readonly property int fontSizeBody: 14
    readonly property int fontSizeLarge: 18
    readonly property int fontSizeTitle: 30

    // Geometry
    readonly property int spacingSmall: 6
    readonly property int spacing: 12
    readonly property int spacingLarge: 24
    readonly property int radius: 6
    readonly property int topBarHeight: 48

    // Action labels on seats
    readonly property color actionFold: "#8a837a"
    readonly property color actionCheck: "#9fb8a6"
    readonly property color actionCall: "#7fc29b"
    readonly property color actionRaise: "#e2c27e"
    readonly property color actionAllIn: "#e0705f"

    // Motion
    readonly property int durationFast: 120
    readonly property int durationNormal: 220

    // 12345 -> "12,345" (chip amounts are always whole numbers).
    function formatChips(amount) {
        return Number(amount || 0).toLocaleString(Qt.locale("en_US"), "f", 0)
    }

    // Colour for a seat's last-action label ("Raise 120", "Fold", ...).
    function actionColor(label) {
        const word = (label || "").split(" ")[0].toLowerCase()
        switch (word) {
        case "fold": return actionFold
        case "check": return actionCheck
        case "call": return actionCall
        case "bet":
        case "raise": return actionRaise
        case "all-in": return actionAllIn
        default: return textSecondary
        }
    }
}
