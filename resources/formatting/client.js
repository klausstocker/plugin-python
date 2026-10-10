// Replace through Ace's session to keep the edit in its undo history.
function replaceCode(target, code) {
    if (target.editor) {
        const session = target.editor.session;
        const Range = window.ace.require("ace/range").Range;
        const lastRow = session.getLength() - 1;
        target.editor.startOperation();
        try {
            session.markUndoGroup();
            session.replace(new Range(0, 0, lastRow, session.getLine(lastRow).length), code);
            session.markUndoGroup();
        } finally {
            target.editor.endOperation();
        }
    } else {
        target.textarea.value = code;
        target.textarea.dispatchEvent(new Event("input", { bubbles: true }));
    }
}

export function bindFormatButton({ button, output, getTarget, requestFormat, onChange }) {
    const refresh = () => {
        button.disabled = button.dataset.requestPending === "true" || !getTarget();
    };
    button.addEventListener("click", async () => {
        const target = getTarget();
        if (!target || button.dataset.requestPending === "true") return;
        const read = () => target.editor ? target.editor.getValue() : target.textarea.value;
        const original = read();
        const label = button.textContent;
        button.dataset.requestPending = "true";
        button.textContent = "Formatting…";
        refresh();
        try {
            const formatted = await requestFormat(original, target.filename);
            if (!button.isConnected) return;
            if (read() !== original) {
                output.textContent = "Code changed while formatting. Please try again.";
                return;
            }
            if (formatted !== original) replaceCode(target, formatted);
            if (onChange) onChange();
            output.textContent = "Code formatted.";
        } catch (error) {
            if (button.isConnected) output.textContent = "Formatting failed: " + (error.message || error);
        } finally {
            delete button.dataset.requestPending;
            button.textContent = label;
            refresh();
        }
    });
    refresh();
    return refresh;
}
