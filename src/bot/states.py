from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_llm_session = State()

class LLMSessionStates(StatesGroup):
    active_session = State()