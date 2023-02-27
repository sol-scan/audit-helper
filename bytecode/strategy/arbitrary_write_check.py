from mythril.support.model import get_model
from mythril.exceptions import UnsatError
from mythril.laser.ethereum.state.global_state import GlobalState
from bytecode.strategy.base import deploy_contract, global_state_handle

def _arbitrary_write_handler(global_state_trace:GlobalState):
    constraints = global_state_trace.world_state.constraints
    constraints.append(global_state_trace.mstate.stack[-1]<global_state_trace.mstate.stack[-2])
    try:
        model = get_model(tuple(constraints), enforce_execution_time = False)
        print(global_state_trace.get_current_instruction())
    except UnsatError as e:
        pass

def arbitrary_write_check(deployed_code:str):
    world_state, caller_account = deploy_contract(deployed_code)
    global_states_final = global_state_handle(world_state,caller_account,'SSTORE',_arbitrary_write_handler)
    for global_state_final in global_states_final:
        global_state_handle(global_state_final.world_state, caller_account, 'SSTORE', _arbitrary_write_handler)