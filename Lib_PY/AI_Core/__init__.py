"""
Library:         __init__.py
Family:          AI_Core
Module Purpose:  Package entry point for BEJSON 105 Multi-AI Provider Gateway prototypes.
Architecture:    3-Tier AI Gateway (Dispatcher/Translator -> Pre/Post Gates + Tooling/Parser/Extension Registries -> JIT Key/Rotator/Vault/Clients)
Version:         2.1.1
Release_Version: 301
Date:            2026-11-19
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   04414238-9e2d-4268-98ce-c72c0376566c
"""
from lib_bejson_AI_Core_errors import (  # noqa: F401
    AIException,
    ERR_AI_HTTP_AUTH_FAILED,
    ERR_AI_HTTP_RATE_LIMITED,
    ERR_AI_KEY_MISSING,
    ERR_AI_PROVIDER_NOT_REGISTERED,
    ERR_AI_RENDERER_FAILED,
    ERR_AI_RENDERER_NOT_FOUND,
    ERR_AI_SUCCESS,
    ERR_AI_TOOL_EXECUTION_FAILED,
    ERR_AI_TOOLING_DISABLED,
    ERR_AI_TOOLING_SYSTEM_NOT_FOUND,
)
from lib_bejson_AI_Core_client_base import BaseAIClient  # noqa: F401
from lib_bejson_AI_Core_client_geminiinteractions import (  # noqa: F401
    Gemini_Interactions_Client,
    GeminiInteractionsClient,
)
from lib_bejson_AI_Core_client_geminirest import (  # noqa: F401
    Gemini_Rest_Client,
    GeminiRestClient,
)
from lib_bejson_AI_Core_dispatcher import (  # noqa: F401
    AIDispatcher,
    AI_Dispatch,
    AI_Dispatch_Async,
    AI_Dispatcher,
    Get_Interaction_ID,
    Get_Rendered_Output,
    Get_Response_JSON,
    Get_Response_Text,
    Get_Response_Usage,
    Get_Tool_Calls,
    Get_Turn_Continuation_Command,
)
from lib_bejson_AI_Core_env_vault import AIEnvVault  # noqa: F401
from lib_bejson_AI_Core_extension_parser import (  # noqa: F401
    Base_Extension_Module_Parser,
    BaseExtensionModuleParser,
    Extension_Parser_Registry,
    ExtensionParserRegistry,
)
from lib_bejson_AI_Core_features_common import (  # noqa: F401
    build_bejson_105_ai_request,
    build_bejson_105_ai_response,
)
from lib_bejson_AI_Core_jit_key_handler import JITKeyHandler, mask_key  # noqa: F401
from lib_bejson_AI_Core_key_rotator import KeyHealthRecord, KeyRotator  # noqa: F401
from lib_bejson_AI_Core_models import (  # noqa: F401
    Antigravity_Preview_Latest,
    DEFAULT_TEXT_MODEL,
    Gemini_3_1_Flash_Lite,
    Gemini_3_5_Flash_Lite,
    Gemini_3_6_Flash,
    Gemini_3_7_Flash,
    Gemini_3_8_Flash,
    Gemini_4_Argon,
    Gemini_4_Hydrogen,
    Gemini_Flash_Latest,
    Gemini_Flash_Lite_Latest,
    Gemini_Pro_Latest,
    Gemma_4_31B,
    List_Active_Gemini_Models,
    Query_Live_Gemini_Models,
    Resolve_Model_Identifier,
)
from lib_bejson_AI_Core_context_bubble import (  # noqa: F401
    BubbleContext,
    BubbleIntegrityError,
    ContextBubblePreParser,
    KEEP_END,
    KEEP_START,
    REFRESH_STABLE,
    REFRESH_TURN,
    ai_bubble_allocate,
    ai_bubble_clear_allotments,
    ai_bubble_config_init,
    ai_bubble_config_load,
    ai_bubble_config_update,
    ai_bubble_destroy,
    ai_bubble_get_state,
    ai_bubble_init,
    ai_bubble_prepare,
    ai_bubble_preview,
    ai_bubble_register_allotment,
    ai_bubble_registered_names,
    ai_bubble_unregister_allotment,
)
from lib_bejson_AI_Core_context_files import (  # noqa: F401
    ai_attachment_files_delete,
    ai_attachment_files_import,
    ai_attachment_files_init,
    ai_attachment_files_list,
    ai_attachment_files_read,
    ai_attachment_files_toggle,
    ai_attachment_files_uncheck_all,
    ai_attachment_files_update_content,
    ai_context_files_build_section,
    ai_context_files_delete,
    ai_context_files_import,
    ai_context_files_init,
    ai_context_files_list,
    ai_context_files_read,
    ai_context_files_toggle,
)
from lib_bejson_AI_Core_bubble_allotments import (  # noqa: F401
    DIRECTIVES,
    register_builtin_allotments,
)
from lib_bejson_AI_Core_parser_base import (  # noqa: E402, F401
    Base_Modular_Parser,
    BaseModularParser,
)
from lib_bejson_AI_Core_parser_registry import (  # noqa: F401
    Parser_Registry,
    ParserRegistry,
)
from lib_bejson_AI_Core_plugin_base import Base_Plugin, BasePlugin  # noqa: F401
from lib_bejson_AI_Core_plugin_registry import Plugin_Registry, PluginRegistry  # noqa: F401
from lib_bejson_AI_Core_plugin_schema import (  # noqa: F401
    PLUGIN_API_VERSION,
    PLUGIN_STAGES,
    plugin_manifest_new,
    plugin_manifest_validate,
)
from lib_bejson_AI_Core_postprocessor import AIPostprocessor  # noqa: F401
from lib_bejson_AI_Core_preprocessor import AIPreprocessor  # noqa: F401
from lib_bejson_AI_Core_renderer_base import (  # noqa: F401
    Base_Renderer,
    BaseRenderer,
)
from lib_bejson_AI_Core_renderer_registry import (  # noqa: F401
    Renderer_Registry,
    RendererRegistry,
)
from lib_bejson_AI_Core_tooling_base import (  # noqa: F401
    Base_Tooling_System,
    BaseToolingSystem,
)
from lib_bejson_AI_Core_tooling_interactions import (  # noqa: F401
    Interactions_Tooling_System,
    InteractionsToolingSystem,
)
from lib_bejson_AI_Core_tooling_registry import (  # noqa: F401
    AI_Global_Config_Manager,
    AIGlobalConfigManager,
    Tooling_Registry,
    ToolingRegistry,
)
from lib_bejson_AI_Core_translator import (  # noqa: F401
    AI_Translator,
    AITranslator,
)

