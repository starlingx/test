from typing import Any

from framework.web.action.web_action import WebAction


class WebActionSetTextJs(WebAction):
    """
    Class representing a Web action of setting an element's value using JavaScript.

    Used for framework-managed inputs and textareas where incremental key entry
    races with the component's re-render and scrambles the caret position. The
    value is set through the element prototype's native value setter and native
    input and change events are dispatched, so a component that tracks its value
    through a cached setter (such as React) registers the change and updates its
    internal state. Setting the value property directly is not sufficient for such
    components: the DOM updates but the component's change handler never fires and
    its state is written back over the value on the next render.
    """

    def perform_action(self, web_element: Any, *args: Any) -> None:
        """
        Override the parent's perform action - Sets the value of the element via JavaScript.

        Args:
            web_element (Any): Element to set the value of.
            *args (Any): One 'str' argument; the text to set in the web_element.

        Returns: None

        """
        text_to_set = args[0]
        self.webdriver.execute_script(
            "var element = arguments[0];"
            "var value = arguments[1];"
            "var prototype = element.tagName === 'TEXTAREA'"
            "    ? window.HTMLTextAreaElement.prototype"
            "    : window.HTMLInputElement.prototype;"
            "var valueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;"
            "valueSetter.call(element, value);"
            "element.dispatchEvent(new Event('input', { bubbles: true }));"
            "element.dispatchEvent(new Event('change', { bubbles: true }));",
            web_element,
            text_to_set,
        )

    def __str__(self) -> str:
        """
        String representation of this action.

        Returns:
            str:
        """
        return "SetTextJs"
