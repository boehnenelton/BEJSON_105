"""
Library:        lib_bejson_Browser_browser_core.py
Family:         Browser
Description:    Unified Playwright session driver and 105a row-by-row playbook execution engine.
Version:        1.0.0
Date:           2026-11-21
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  6fa0d0bc-2201-48e1-9891-9f7ee8051faa
Release_Version: 300
License:        PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Optional, Union

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

# Sibling family resolution for Core and Browser
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
for _family_name in ("Core", "Browser"):
    _family_path = os.path.normpath(os.path.join(_CURRENT_DIR, "..", _family_name))
    if os.path.isdir(_family_path) and _family_path not in sys.path:
        sys.path.insert(0, _family_path)

from lib_bejson_Core_bejson_core import (
    bejson_core_atomic_write,
    bejson_core_get_field_map,
)
from lib_bejson_Browser_browser_errors import (
    ERR_BROWSER_ACTION_TIMEOUT,
    ERR_BROWSER_IO_FAILURE,
    ERR_BROWSER_LAUNCH_FAILED,
    ERR_BROWSER_LOCATOR_NOT_FOUND,
    ERR_BROWSER_SCHEMA_INVALID,
    ERR_BROWSER_SUCCESS,
    ERR_BROWSER_UNKNOWN_VERB,
    BrowserLibraryError,
)
from lib_bejson_Browser_browser_validator import validate_browser_playbook

logger: logging.Logger = logging.getLogger("BrowserPlaybookCore")


# ---------------------------------------------------------------------------
# Unified Termux/Desktop Playwright Driver (BrowserSession)
# ---------------------------------------------------------------------------
class BrowserSession:
    """
    Unified async context manager managing Playwright browser driver lifecycle
    across native Android Termux and desktop environments.
    """

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        default_timeout_ms: int = 30000,
        user_agent: Optional[str] = None,
        storage_state_path: Optional[str] = None,
    ) -> None:
        self.headless: bool = headless
        self.viewport_width: int = viewport_width
        self.viewport_height: int = viewport_height
        self.default_timeout_ms: int = default_timeout_ms
        self.user_agent: Optional[str] = user_agent
        self.storage_state_path: Optional[str] = storage_state_path

        self.pw_cm: Any = None
        self.pw_driver: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.is_termux: bool = False

    async def __aenter__(self) -> "BrowserSession":
        # Check native Termux Playwright first, then fallback to standard playwright
        try:
            from termux_playwright import async_playwright_termux, launch
            self.pw_cm = async_playwright_termux()
            self.is_termux = True
        except ImportError:
            try:
                from playwright.async_api import async_playwright
                self.pw_cm = async_playwright()
                self.is_termux = False
            except ImportError as import_err:
                raise BrowserLibraryError(
                    ERR_BROWSER_LAUNCH_FAILED,
                    f"Neither termux_playwright nor playwright is installed: {import_err}"
                ) from import_err

        try:
            self.pw_driver = await self.pw_cm.__aenter__()
            if self.is_termux:
                from termux_playwright import launch
                self.browser = await launch(self.pw_driver, headless=self.headless)
            else:
                self.browser = await self.pw_driver.chromium.launch(headless=self.headless)

            context_kwargs: Dict[str, Any] = {
                "viewport": {"width": self.viewport_width, "height": self.viewport_height}
            }
            if self.user_agent:
                context_kwargs["user_agent"] = self.user_agent
            if self.storage_state_path and os.path.isfile(self.storage_state_path):
                context_kwargs["storage_state"] = self.storage_state_path

            self.context = await self.browser.new_context(**context_kwargs)
            self.context.set_default_timeout(self.default_timeout_ms)
            self.page = await self.context.new_page()
            return self
        except Exception as launch_err:
            await self._cleanup()
            raise BrowserLibraryError(
                ERR_BROWSER_LAUNCH_FAILED,
                f"Failed to initialize Playwright browser session: {launch_err}"
            ) from launch_err

    async def _cleanup(self) -> None:
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.pw_cm:
            try:
                await self.pw_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self.pw_cm = None

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._cleanup()


def run_with_browser(
    coroutine_func: Callable[[Any], Any],
    **session_kwargs: Any
) -> Any:
    """
    Thin sync helper executing an async function against a fresh BrowserSession page.
    Enables consumers like Lib_PY/Metrics to perform Playwright actions without duplicating setup.
    """
    async def _executor() -> Any:
        async with BrowserSession(**session_kwargs) as session:
            return await coroutine_func(session.page)

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop and running_loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool_executor:
            future = pool_executor.submit(asyncio.run, _executor())
            return future.result()
    return asyncio.run(_executor())


# ---------------------------------------------------------------------------
# Row-By-Row Dispatcher Helpers
# ---------------------------------------------------------------------------
def _interpolate_string(template_string: str, session_variables: Dict[str, Any]) -> str:
    """
    Interpolates {{var_key}} tokens inside a string using the current in-memory session dict.
    """
    if not template_string or "{{" not in template_string:
        return template_string

    def _replace_token(token_match: re.Match[str]) -> str:
        variable_name = token_match.group(1).strip()
        if variable_name in session_variables:
            return str(session_variables[variable_name])
        return token_match.group(0)

    return re.sub(r"\{\{([a-zA-Z0-9_]+)\}\}", _replace_token, template_string)


def _resolve_page_locator(page: Any, strategy: str, value: str) -> Any:
    """
    Resolves a Playwright locator from strategy and selector value.
    """
    strategy_clean = strategy.strip().lower()
    val_clean = value.strip()

    if strategy_clean == "css":
        return page.locator(val_clean)
    elif strategy_clean == "role":
        return page.get_by_role(val_clean)
    elif strategy_clean == "text":
        return page.get_by_text(val_clean)
    elif strategy_clean == "testid":
        return page.get_by_test_id(val_clean)
    elif strategy_clean == "xpath":
        return page.locator(f"xpath={val_clean}")
    elif strategy_clean == "none" or not strategy_clean:
        return None
    else:
        raise BrowserLibraryError(
            ERR_BROWSER_SCHEMA_INVALID,
            f"Unsupported locator strategy: {strategy}"
        )


# ---------------------------------------------------------------------------
# Playbook Execution Engine
# ---------------------------------------------------------------------------
async def run_browser_playbook_async(
    playbook_path: Union[str, Path],
    vars_override: Optional[Dict[str, Any]] = None,
    resume: bool = True
) -> Dict[str, Any]:
    """
    Asynchronous row-by-row execution engine for BEJSON 105a Browser Playbooks.
    Loads and validates the document, sorts rows by step_index, executes actions,
    and atomically persists progress after every step.
    """
    resolved_path = Path(playbook_path).resolve()
    if not resolved_path.exists():
        raise BrowserLibraryError(
            ERR_BROWSER_IO_FAILURE,
            f"Playbook file not found: {resolved_path}"
        )

    # 1. Load and validate the 105a playbook document
    validation_result = validate_browser_playbook(resolved_path, is_file=True)
    if not validation_result.valid:
        error_summary = "; ".join(validation_result.errors[:3])
        raise BrowserLibraryError(
            ERR_BROWSER_SCHEMA_INVALID,
            f"Playbook validation failed: {error_summary}"
        )

    try:
        with open(resolved_path, "r", encoding="utf-8") as file_read_handle:
            playbook_document: Dict[str, Any] = json.load(file_read_handle)
    except Exception as read_err:
        raise BrowserLibraryError(
            ERR_BROWSER_IO_FAILURE,
            f"Failed to read playbook document: {read_err}"
        ) from read_err

    # 2. Compile O(1) field map cache once
    field_map: Dict[str, int] = bejson_core_get_field_map(playbook_document)
    step_col_index = field_map["step_index"]

    # 3. Sort rows by step_index
    rows: List[List[Any]] = playbook_document.get("Values", [])
    rows.sort(key=lambda item_row: item_row[step_col_index])

    # 4. Initialize session variables dictionary
    session_variables: Dict[str, Any] = dict(vars_override) if vars_override else {}

    # 5. Extract Session_Config for browser launch
    config_dict = playbook_document.get("Session_Config", {})
    headless_setting = bool(config_dict.get("headless", True))
    viewport_width = int(config_dict.get("viewport_width", 1280))
    viewport_height = int(config_dict.get("viewport_height", 720))
    default_timeout = int(config_dict.get("default_timeout_ms", 30000))
    user_agent_setting = config_dict.get("user_agent") or None
    storage_state_setting = config_dict.get("storage_state_path") or None

    # 6. Execute actions within a single BrowserSession
    async with BrowserSession(
        headless=headless_setting,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        default_timeout_ms=default_timeout,
        user_agent=user_agent_setting,
        storage_state_path=storage_state_setting,
    ) as session:
        page = session.page

        # Track the most recent completed navigation URL for session restoration on resume
        last_completed_nav_url: Optional[str] = None
        for prior_row in rows:
            if bool(prior_row[field_map["is_completed"]]) and str(prior_row[field_map["action_verb"]]).strip() == "goto":
                candidate_url = str(prior_row[field_map["locator_value"]]).strip() or str(prior_row[field_map["input_payload"]]).strip()
                if candidate_url:
                    last_completed_nav_url = _interpolate_string(candidate_url, session_variables)

        for current_row in rows:
            is_completed_flag = bool(current_row[field_map["is_completed"]])
            step_index = current_row[field_map["step_index"]]

            # Skip completed rows if resuming
            if resume and is_completed_flag:
                logger.debug(f"Skipping already completed step {step_index}")
                continue

            # If resuming and page has not navigated away from blank, restore last navigated URL
            if resume and page.url == "about:blank" and last_completed_nav_url:
                logger.info(f"Restoring navigation to {last_completed_nav_url} for resume")
                await page.goto(last_completed_nav_url, timeout=default_timeout)

            raw_verb = str(current_row[field_map["action_verb"]]).strip()
            raw_strategy = str(current_row[field_map["locator_strategy"]]).strip()
            raw_locator_value = str(current_row[field_map["locator_value"]]).strip()
            raw_input_payload = str(current_row[field_map["input_payload"]]).strip()
            timeout_ms = int(current_row[field_map["timeout_ms"]])
            wait_after_ms = int(current_row[field_map["wait_after_ms"]])
            save_var_key = str(current_row[field_map["save_var_key"]]).strip()
            artifact_path_raw = str(current_row[field_map["artifact_path"]]).strip()

            # Variable interpolation
            interpolated_locator_val = _interpolate_string(raw_locator_value, session_variables)
            interpolated_payload = _interpolate_string(raw_input_payload, session_variables)
            interpolated_artifact_path = _interpolate_string(artifact_path_raw, session_variables)

            try:
                # Verb dispatch
                if raw_verb == "goto":
                    target_url = interpolated_locator_val if interpolated_locator_val else interpolated_payload
                    await page.goto(target_url, timeout=timeout_ms)

                elif raw_verb == "click":
                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is None:
                        raise BrowserLibraryError(
                            ERR_BROWSER_LOCATOR_NOT_FOUND,
                            f"Step {step_index}: click action requires a valid locator"
                        )
                    await locator.click(timeout=timeout_ms)

                elif raw_verb == "fill":
                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is None:
                        raise BrowserLibraryError(
                            ERR_BROWSER_LOCATOR_NOT_FOUND,
                            f"Step {step_index}: fill action requires a valid locator"
                        )
                    await locator.fill(interpolated_payload, timeout=timeout_ms)

                elif raw_verb == "select":
                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is None:
                        raise BrowserLibraryError(
                            ERR_BROWSER_LOCATOR_NOT_FOUND,
                            f"Step {step_index}: select action requires a valid locator"
                        )
                    await locator.select_option(interpolated_payload, timeout=timeout_ms)

                elif raw_verb == "press":
                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is not None:
                        await locator.press(interpolated_payload, timeout=timeout_ms)
                    else:
                        await page.keyboard.press(interpolated_payload)

                elif raw_verb == "wait_for":
                    if raw_strategy != "none" and interpolated_locator_val:
                        locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                        await locator.wait_for(timeout=timeout_ms)
                    else:
                        await page.wait_for_timeout(timeout_ms)

                elif raw_verb == "extract_text":
                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is None:
                        raise BrowserLibraryError(
                            ERR_BROWSER_LOCATOR_NOT_FOUND,
                            f"Step {step_index}: extract_text requires a valid locator"
                        )
                    extracted_text = await locator.text_content(timeout=timeout_ms)
                    extracted_result = str(extracted_text) if extracted_text is not None else ""
                    current_row[field_map["extracted_value"]] = extracted_result
                    if save_var_key:
                        session_variables[save_var_key] = extracted_result

                elif raw_verb == "extract_attr":
                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is None:
                        raise BrowserLibraryError(
                            ERR_BROWSER_LOCATOR_NOT_FOUND,
                            f"Step {step_index}: extract_attr requires a valid locator"
                        )
                    attribute_target = interpolated_payload.strip()
                    extracted_attr = await locator.get_attribute(attribute_target, timeout=timeout_ms)
                    extracted_result = str(extracted_attr) if extracted_attr is not None else ""
                    current_row[field_map["extracted_value"]] = extracted_result
                    if save_var_key:
                        session_variables[save_var_key] = extracted_result

                elif raw_verb == "screenshot":
                    target_image_path = interpolated_artifact_path or interpolated_payload
                    if not target_image_path:
                        raise BrowserLibraryError(
                            ERR_BROWSER_IO_FAILURE,
                            f"Step {step_index}: screenshot requires artifact_path or input_payload"
                        )
                    parent_directory = os.path.dirname(os.path.abspath(target_image_path))
                    if parent_directory:
                        os.makedirs(parent_directory, exist_ok=True)

                    locator = _resolve_page_locator(page, raw_strategy, interpolated_locator_val)
                    if locator is not None:
                        await locator.screenshot(path=target_image_path, timeout=timeout_ms)
                    else:
                        await page.screenshot(path=target_image_path, timeout=timeout_ms)
                    current_row[field_map["artifact_path"]] = target_image_path

                elif raw_verb == "eval_js":
                    script_code = interpolated_payload if interpolated_payload else interpolated_locator_val
                    eval_output = await page.evaluate(script_code)
                    if isinstance(eval_output, (str, int, float, bool)):
                        eval_str = str(eval_output)
                    else:
                        eval_str = json.dumps(eval_output)
                    current_row[field_map["extracted_value"]] = eval_str
                    if save_var_key:
                        session_variables[save_var_key] = eval_str

                else:
                    raise BrowserLibraryError(
                        ERR_BROWSER_UNKNOWN_VERB,
                        f"Step {step_index}: unrecognized action_verb '{raw_verb}'"
                    )

                # Post-step settling pause
                if wait_after_ms > 0:
                    await page.wait_for_timeout(wait_after_ms)

                # Mark step success and persist atomically
                current_row[field_map["is_completed"]] = True
                current_row[field_map["error_code"]] = ERR_BROWSER_SUCCESS
                write_success = bejson_core_atomic_write(str(resolved_path), playbook_document)
                if not write_success:
                    raise BrowserLibraryError(
                        ERR_BROWSER_IO_FAILURE,
                        f"Atomic writeback failed for step {step_index}"
                    )

            except Exception as step_exc:
                # Classify error code from exception
                determined_error_code: int = ERR_BROWSER_IO_FAILURE
                if isinstance(step_exc, BrowserLibraryError):
                    determined_error_code = step_exc.code
                else:
                    exception_type_name = type(step_exc).__name__.lower()
                    exception_message = str(step_exc).lower()
                    if "timeout" in exception_type_name or "timeout" in exception_message:
                        determined_error_code = ERR_BROWSER_ACTION_TIMEOUT
                    elif "locator" in exception_message or "waiting for selector" in exception_message:
                        determined_error_code = ERR_BROWSER_LOCATOR_NOT_FOUND
                    elif "launch" in exception_message or "browser" in exception_message:
                        determined_error_code = ERR_BROWSER_LAUNCH_FAILED
                    else:
                        determined_error_code = ERR_BROWSER_SCHEMA_INVALID

                # Record error code on row, write atomically, and halt cleanly
                current_row[field_map["error_code"]] = determined_error_code
                current_row[field_map["is_completed"]] = False
                bejson_core_atomic_write(str(resolved_path), playbook_document)
                raise BrowserLibraryError(
                    determined_error_code,
                    f"Step {step_index} ({raw_verb}) failed: {step_exc}"
                ) from step_exc

    return playbook_document


def run_browser_playbook(
    playbook_path: Union[str, Path],
    vars_override: Optional[Dict[str, Any]] = None,
    resume: bool = True
) -> Dict[str, Any]:
    """
    Synchronous entrypoint for executing a BEJSON 105a Browser Playbook row-by-row.
    Safely executes run_browser_playbook_async in a managed event loop or thread.
    """
    try:
        active_loop = asyncio.get_running_loop()
    except RuntimeError:
        active_loop = None

    if active_loop and active_loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool_executor:
            future_result = pool_executor.submit(
                asyncio.run,
                run_browser_playbook_async(
                    playbook_path=playbook_path,
                    vars_override=vars_override,
                    resume=resume
                )
            )
            return future_result.result()
    else:
        return asyncio.run(
            run_browser_playbook_async(
                playbook_path=playbook_path,
                vars_override=vars_override,
                resume=resume
            )
        )
