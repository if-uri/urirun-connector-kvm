# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from typing import Literal, Optional, Union, Any
from google import genai
from google.genai import types
import termcolor
from google.genai.types import (
    Part,
    GenerateContentConfig,
    Content,
    Candidate,
    FunctionResponse,
    FinishReason,
)
import time
from rich.console import Console
from rich.table import Table

from computers import EnvState, Computer

MAX_RECENT_TURN_WITH_SCREENSHOTS = 3
LEGACY_COMPUTER_USE_MODELS = [
    "gemini-2.5-computer-use-preview-10-2025",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
]

# Legacy predefined functions, which are used in gemini-2.5-computer-use-preview-10-2025, gemini-3-flash-preview and gemini-3.1-pro-preview.
LEGACY_PREDEFINED_COMPUTER_USE_FUNCTIONS = [
    "open_web_browser",
    "click_at",
    "hover_at",
    "type_text_at",
    "scroll_document",
    "scroll_at",
    "wait_5_seconds",
    "go_back",
    "go_forward",
    "search",
    "navigate",
    "key_combination",
    "drag_and_drop",
]

# Predefined functions which are used in gemini-3.5-flash and future models.
PREDEFINED_COMPUTER_USE_FUNCTIONS = [
    "click",
    "double_click",
    "triple_click",
    "middle_click",
    "right_click",
    "mouse_down",
    "mouse_up",
    "move",
    "type",
    "drag_and_drop",
    "wait",
    "press_key",
    "key_down",
    "key_up",
    "hotkey",
    "take_screenshot",
    "scroll",
    "go_back",
    "navigate",
    "go_forward",
]


console = Console()

# Built-in Computer Use tools will return "EnvState".
# Custom provided functions will return "dict".
FunctionResponseT = Union[EnvState, dict]

_XY_CLICK_ACTIONS: dict[str, str] = {
    "click": "click_at",
    "double_click": "double_click_at",
    "triple_click": "triple_click_at",
    "middle_click": "middle_click_at",
    "right_click": "right_click_at",
    "mouse_down": "mouse_down",
    "mouse_up": "mouse_up",
    "move": "hover_at",
}

_SIMPLE_NO_ARG_ACTIONS: dict[str, str] = {
    "open_web_browser": "open_web_browser",
    "go_back": "go_back",
    "go_forward": "go_forward",
    "take_screenshot": "take_screenshot",
    "wait_5_seconds": "wait_5_seconds",
    "search": "search",
}

_KEY_ARG_ACTIONS: dict[str, str] = {
    "press_key": "press_key",
    "key_down": "key_down",
    "key_up": "key_up",
}


def multiply_numbers(x: float, y: float) -> dict:
    """Multiplies two numbers."""
    return {"result": x * y}


class BrowserAgent:
    def __init__(
        self,
        browser_computer: Computer,
        query: str,
        model_name: str,
        verbose: bool = True,
    ):
        self._browser_computer = browser_computer
        self._query = query
        self._model_name = model_name
        self._verbose = verbose
        self.final_reasoning = None
        self._client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
            vertexai=os.environ.get("USE_VERTEXAI", "0").lower() in ["true", "1"],
            project=os.environ.get("VERTEXAI_PROJECT"),
            location=os.environ.get("VERTEXAI_LOCATION"),
        )
        self._contents: list[Content] = [
            Content(
                role="user",
                parts=[
                    Part(text=self._query),
                ],
            )
        ]
        self._use_legacy_computer_use_function_call = (
            model_name in LEGACY_COMPUTER_USE_MODELS
        )

        # Exclude any predefined functions here.
        excluded_predefined_functions = []

        # Add your own custom functions here.
        custom_functions = [
            # For example:
            types.FunctionDeclaration.from_callable(
                client=self._client, callable=multiply_numbers
            )
        ]

        self._generate_content_config = GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER,
                        excluded_predefined_functions=excluded_predefined_functions,
                    ),
                ),
                types.Tool(function_declarations=custom_functions),
            ],
            thinking_config=types.ThinkingConfig(include_thoughts=True),
        )

    def _handle_scroll_at(self, action: types.FunctionCall) -> FunctionResponseT:
        """Shared scroll_at logic for both current and legacy action dispatch."""
        x = self.denormalize_x(action.args["x"])
        y = self.denormalize_y(action.args["y"])
        magnitude = action.args.get("magnitude", 800)
        direction = action.args["direction"]
        if direction in ("up", "down"):
            magnitude = self.denormalize_y(magnitude)
        elif direction in ("left", "right"):
            magnitude = self.denormalize_x(magnitude)
        else:
            raise ValueError("Unknown direction: ", direction)
        return self._browser_computer.scroll_at(x=x, y=y, direction=direction, magnitude=magnitude)

    def _handle_drag_and_drop(self, action: types.FunctionCall) -> FunctionResponseT:
        return self._browser_computer.drag_and_drop(
            x=self.denormalize_x(action.args["x"]),
            y=self.denormalize_y(action.args["y"]),
            destination_x=self.denormalize_x(action.args["destination_x"]),
            destination_y=self.denormalize_y(action.args["destination_y"]),
        )

    def _dispatch_action(self, action: types.FunctionCall) -> FunctionResponseT:
        """Dispatch a non-legacy action by name."""
        bc = self._browser_computer
        name = action.name
        if name in _XY_CLICK_ACTIONS:
            x = self.denormalize_x(action.args["x"])
            y = self.denormalize_y(action.args["y"])
            return getattr(bc, _XY_CLICK_ACTIONS[name])(x=x, y=y)
        if name in _SIMPLE_NO_ARG_ACTIONS:
            return getattr(bc, _SIMPLE_NO_ARG_ACTIONS[name])()
        if name in _KEY_ARG_ACTIONS:
            return getattr(bc, _KEY_ARG_ACTIONS[name])(action.args["key"])
        if name == "scroll":
            return self._handle_scroll_at(action)
        if name == "drag_and_drop":
            return self._handle_drag_and_drop(action)
        if name == "type":
            return bc.type_text(text=action.args["text"], press_enter=action.args.get("press_enter", False))
        if name == "wait":
            return bc.wait(int(action.args.get("seconds", 1)))
        if name == "navigate":
            return bc.navigate(action.args["url"])
        if name == "hotkey":
            return bc.key_combination(action.args["keys"])
        if name == multiply_numbers.__name__:
            return multiply_numbers(x=action.args["x"], y=action.args["y"])
        raise ValueError(f"Unsupported function: {action}")

    def _dispatch_legacy_action(self, action: types.FunctionCall) -> FunctionResponseT:
        """Dispatch a legacy action by name."""
        bc = self._browser_computer
        name = action.name
        if name in _SIMPLE_NO_ARG_ACTIONS:
            return getattr(bc, _SIMPLE_NO_ARG_ACTIONS[name])()
        if name == "click_at":
            return bc.click_at(x=self.denormalize_x(action.args["x"]), y=self.denormalize_y(action.args["y"]))
        if name == "hover_at":
            return bc.hover_at(x=self.denormalize_x(action.args["x"]), y=self.denormalize_y(action.args["y"]))
        if name == "type_text_at":
            return bc.type_text_at(
                x=self.denormalize_x(action.args["x"]),
                y=self.denormalize_y(action.args["y"]),
                text=action.args["text"],
                press_enter=action.args.get("press_enter", False),
                clear_before_typing=action.args.get("clear_before_typing", True),
            )
        if name == "scroll_document":
            return bc.scroll_document(action.args["direction"])
        if name == "scroll_at":
            return self._handle_scroll_at(action)
        if name == "drag_and_drop":
            return self._handle_drag_and_drop(action)
        if name == "navigate":
            return bc.navigate(action.args["url"])
        if name == "key_combination":
            return bc.key_combination(action.args["keys"].split("+"))
        if name == multiply_numbers.__name__:
            return multiply_numbers(x=action.args["x"], y=action.args["y"])
        raise ValueError(f"Unsupported function: {action}")

    def handle_action(
        self, action: types.FunctionCall, use_legacy_actions: bool
    ) -> FunctionResponseT:
        """Handles the action and returns the environment state."""
        if use_legacy_actions:
            return self.handle_legacy_action(action)
        return self._dispatch_action(action)

    def handle_legacy_action(self, action: types.FunctionCall) -> FunctionResponseT:
        """Handles the action defined in the legacy models, and returns the environment state."""
        return self._dispatch_legacy_action(action)

    def get_model_response(
        self, max_retries=5, base_delay_s=1
    ) -> types.GenerateContentResponse:
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=self._contents,
                    config=self._generate_content_config,
                )
                return response  # Return response on success
            except Exception as e:
                print(e)
                if attempt < max_retries - 1:
                    delay = base_delay_s * (2**attempt)
                    message = (
                        f"Generating content failed on attempt {attempt + 1}. "
                        f"Retrying in {delay} seconds...\n"
                    )
                    termcolor.cprint(
                        message,
                        color="yellow",
                    )
                    time.sleep(delay)
                else:
                    termcolor.cprint(
                        f"Generating content failed after {max_retries} attempts.\n",
                        color="red",
                    )
                    raise

    def get_text(self, candidate: Candidate) -> Optional[str]:
        """Extracts the text from the candidate."""
        if not candidate.content or not candidate.content.parts:
            return None
        text = []
        for part in candidate.content.parts:
            if part.text:
                text.append(part.text)
        return " ".join(text) or None

    def extract_function_calls(self, candidate: Candidate) -> list[types.FunctionCall]:
        """Extracts the function call from the candidate."""
        if not candidate.content or not candidate.content.parts:
            return []
        ret = []
        for part in candidate.content.parts:
            if part.function_call:
                ret.append(part.function_call)
        return ret

    def _build_function_response(
        self,
        function_call: types.FunctionCall,
        fc_result: FunctionResponseT,
        extra_fr_fields: dict,
    ) -> Optional[FunctionResponse]:
        """Build a FunctionResponse from an action result, or None if unrecognised."""
        if isinstance(fc_result, EnvState):
            return FunctionResponse(
                name=function_call.name,
                response={"url": fc_result.url, **extra_fr_fields},
                parts=[
                    types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png", data=fc_result.screenshot
                        )
                    )
                ],
            )
        if isinstance(fc_result, dict):
            return FunctionResponse(name=function_call.name, response=fc_result)
        return None

    def _trim_old_screenshots(self) -> None:
        """Remove screenshot data from turns older than MAX_RECENT_TURN_WITH_SCREENSHOTS."""
        turn_with_screenshots_found = 0
        for content in reversed(self._contents):
            if not (content.role == "user" and content.parts):
                continue
            has_screenshot = any(
                part.function_response
                and part.function_response.parts
                and part.function_response.name
                in (PREDEFINED_COMPUTER_USE_FUNCTIONS + LEGACY_PREDEFINED_COMPUTER_USE_FUNCTIONS)
                for part in content.parts
            )
            if not has_screenshot:
                continue
            turn_with_screenshots_found += 1
            if turn_with_screenshots_found > MAX_RECENT_TURN_WITH_SCREENSHOTS:
                for part in content.parts:
                    if (
                        part.function_response
                        and part.function_response.parts
                        and part.function_response.name
                        in (PREDEFINED_COMPUTER_USE_FUNCTIONS + LEGACY_PREDEFINED_COMPUTER_USE_FUNCTIONS)
                    ):
                        part.function_response.parts = None

    def run_one_iteration(self) -> Literal["COMPLETE", "CONTINUE"]:
        # Generate a response from the model.
        if self._verbose:
            with console.status(
                "Generating response from Gemini Computer Use...", spinner_style=None
            ):
                try:
                    response = self.get_model_response()
                except Exception as e:
                    return "COMPLETE"
        else:
            try:
                response = self.get_model_response()
            except Exception as e:
                return "COMPLETE"

        if not response.candidates:
            if (
                response.prompt_feedback
                and response.prompt_feedback.block_reason == types.BlockReason.SAFETY
            ):
                raise ValueError(
                    f"Response was blocked due to safety. Feedback: {response.prompt_feedback}"
                )
            print("Response has no candidates!")
            print(response)
            raise ValueError("Empty response")

        # Extract the text and function call from the response.
        candidate = response.candidates[0]
        # Append the model turn to conversation history.
        if candidate.content:
            self._contents.append(candidate.content)

        reasoning = self.get_text(candidate)
        function_calls = self.extract_function_calls(candidate)

        # Retry the request in case of malformed FCs.
        if (
            not function_calls
            and not reasoning
            and candidate.finish_reason == FinishReason.MALFORMED_FUNCTION_CALL
        ):
            return "CONTINUE"

        if not function_calls:
            print(f"Agent Loop Complete: {reasoning}")
            self.final_reasoning = reasoning
            return "COMPLETE"

        function_call_strs = []
        for function_call in function_calls:
            # Print the function call and any reasoning.
            function_call_str = f"Name: {function_call.name}"
            if function_call.args:
                function_call_str += f"\nArgs:"
                for key, value in function_call.args.items():
                    function_call_str += f"\n  {key}: {value}"
            function_call_strs.append(function_call_str)

        table = Table(expand=True)
        table.add_column(
            "Gemini Computer Use Reasoning", header_style="magenta", ratio=1
        )
        table.add_column("Function Call(s)", header_style="cyan", ratio=1)
        table.add_row(reasoning, "\n".join(function_call_strs))
        if self._verbose:
            console.print(table)
            print()

        function_responses = []
        for function_call in function_calls:
            extra_fr_fields = {}
            if function_call.args and (safety := function_call.args.get("safety_decision")):
                decision = self._get_safety_confirmation(safety)
                if decision == "TERMINATE":
                    print("Terminating agent loop")
                    return "COMPLETE"
                extra_fr_fields["safety_acknowledgement"] = "true"
            if self._verbose:
                with console.status("Sending command to Computer...", spinner_style=None):
                    fc_result = self.handle_action(function_call, self._use_legacy_computer_use_function_call)
            else:
                fc_result = self.handle_action(function_call, self._use_legacy_computer_use_function_call)
            fr = self._build_function_response(function_call, fc_result, extra_fr_fields)
            if fr is not None:
                function_responses.append(fr)

        self._contents.append(
            Content(role="user", parts=[Part(function_response=fr) for fr in function_responses])
        )
        self._trim_old_screenshots()
        return "CONTINUE"

    def _get_safety_confirmation(
        self, safety: dict[str, Any]
    ) -> Literal["CONTINUE", "TERMINATE"]:
        if safety["decision"] != "require_confirmation":
            raise ValueError(f"Unknown safety decision: safety['decision']")
        termcolor.cprint(
            "Safety service requires explicit confirmation!",
            color="yellow",
            attrs=["bold"],
        )
        print(safety["explanation"])
        decision = ""
        while decision.lower() not in ("y", "n", "ye", "yes", "no"):
            decision = input("Do you wish to proceed? [Yes]/[No]\n")
        if decision.lower() in ("n", "no"):
            return "TERMINATE"
        return "CONTINUE"

    def agent_loop(self):
        status = "CONTINUE"
        while status == "CONTINUE":
            status = self.run_one_iteration()

    def denormalize_x(self, x: int) -> int:
        return int(x / 1000 * self._browser_computer.screen_size()[0])

    def denormalize_y(self, y: int) -> int:
        return int(y / 1000 * self._browser_computer.screen_size()[1])
