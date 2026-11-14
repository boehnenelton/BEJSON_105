"""
Library:         __init__.py
Family:          AI
Module Purpose:  Package entry point for BEJSON 105 Multi-AI Provider Gateway prototypes.
Architecture:    3-Tier AI Gateway (Dispatcher/Translator -> Pre/Post Gates + Tooling/Parser/Extension Registries -> JIT Key/Rotator/Vault/Clients)
Version:         1.5.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   e2f0b239-6d0b-425f-d25c-1a4b6c0e2011
"""
from lib_bejson_AI_bejson_errors import (  # noqa: F401
    AIException,
    ERR_AI_HTTP_AUTH_FAILED,
    ERR_AI_HTTP_RATE_LIMITED,
    ERR_AI_KEY_MISSING,
    ERR_AI_PROVIDER_NOT_REGISTERED,
    ERR_AI_SUCCESS,
    ERR_AI_TOOL_EXECUTION_FAILED,
    ERR_AI_TOOLING_DISABLED,
    ERR_AI_TOOLING_SYSTEM_NOT_FOUND,
)
from lib_bejson_ai_client_base import BaseAIClient  # noqa: F401
from lib_bejson_ai_client_geminiinteractions import (  # noqa: F401
    Gemini_Interactions_Client,
    GeminiInteractionsClient,
)
from lib_bejson_ai_client_geminirest import (  # noqa: F401
    Gemini_Rest_Client,
    GeminiRestClient,
)
from lib_bejson_ai_dispatcher import (  # noqa: F401
    AIDispatcher,
    AI_Dispatch,
    AI_Dispatch_Async,
    AI_Dispatcher,
    Get_Interaction_ID,
    Get_Response_JSON,
    Get_Response_Text,
    Get_Response_Usage,
    Get_Tool_Calls,
    Get_Turn_Continuation_Command,
)
from lib_bejson_ai_env_vault import AIEnvVault  # noqa: F401
from lib_bejson_ai_extension_parser import (  # noqa: F401
    Base_Extension_Module_Parser,
    BaseExtensionModuleParser,
    Extension_Parser_Registry,
    ExtensionParserRegistry,
)
from lib_bejson_ai_features_common import (  # noqa: F401
    build_bejson_105_ai_request,
    build_bejson_105_ai_response,
)
from lib_bejson_ai_jit_key_handler import JITKeyHandler, mask_key  # noqa: F401
from lib_bejson_ai_key_rotator import KeyHealthRecord, KeyRotator  # noqa: F401
from lib_bejson_ai_models import (  # noqa: F401
    Antigravity_Preview_Latest,
    Gemini_3_1_Flash_Lite,
    Gemini_3_5_Flash_Lite,
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
from lib_bejson_ai_parser_base import (  # noqa: F401
    Base_Modular_Parser,
    BaseModularParser,
)
from lib_bejson_ai_parser_registry import (  # noqa: F401
    Parser_Registry,
    ParserRegistry,
)
from lib_bejson_ai_postprocessor import AIPostprocessor  # noqa: F401
from lib_bejson_ai_preprocessor import AIPreprocessor  # noqa: F401
from lib_bejson_ai_tooling_base import (  # noqa: F401
    Base_Tooling_System,
    BaseToolingSystem,
)
from lib_bejson_ai_tooling_interactions import (  # noqa: F401
    Interactions_Tooling_System,
    InteractionsToolingSystem,
)
from lib_bejson_ai_tooling_registry import (  # noqa: F401
    AI_Global_Config_Manager,
    AIGlobalConfigManager,
    Tooling_Registry,
    ToolingRegistry,
)
from lib_bejson_ai_translator import (  # noqa: F401
    AI_Translator,
    AITranslator,
)
