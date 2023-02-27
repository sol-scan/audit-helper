from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.ethereum.state.calldata import SymbolicCalldata
from mythril.laser.ethereum.transaction import (
    TransactionStartSignal,
    TransactionEndSignal
)
from mythril.laser.ethereum.evm_exceptions import VmException
from mythril.laser.ethereum.instruction_data import get_required_stack_elements
from mythril.laser.ethereum.state.constraints import Constraints

from mythril.laser.smt import Bool, Or, symbol_factory, Solver, is_true
import z3
solver = Solver()

from eth_utils.abi import function_signature_to_4byte_selector

from typing import List, Tuple, Mapping, Callable
import logging

from bytecode.instrction import Instruction

def jumpi_filter(global_state:GlobalState)->bool:
    solver.reset()
    solver.add(*(global_state.world_state.constraints))
    return z3.sat == solver.check()

def state_exec(global_state_cur: GlobalState, pre_hooks: List[Callable]=None) -> Tuple[List[GlobalState], List[GlobalState], Instruction]: 
    instructions = global_state_cur.environment.code.instruction_list
    try:
        instruction = instructions[global_state_cur.mstate.pc]
    except IndexError:
        logging.warn(f'{global_state_cur.current_transaction} -> pc{global_state_cur.mstate.pc}索引越界，视为正常结束')
        return [], [global_state_cur], None

    op_code = instruction['opcode']
    
    if len(global_state_cur.mstate.stack) < get_required_stack_elements(op_code):
        logging.error(f'{global_state_cur.current_transaction} -> {instruction} -> 操作码所需stack长度不足')
        return [], [], instruction

    try:
        new_global_states = Instruction(
            op_code, None, pre_hooks).evaluate(global_state_cur)
    except VmException:
        logging.error(f'{global_state_cur.current_transaction} -> {instruction} -> 虚拟机异常')
        return [], [], instruction
    except TransactionStartSignal:
        return [], [], instruction
    except TransactionEndSignal as end_signal:
        if not end_signal.revert:
            return [], [end_signal.global_state], instruction
        return [], [], instruction
    
    if op_code == 'JUMPI':
        new_global_states = list(filter(jumpi_filter, new_global_states))

    return new_global_states, [], instruction

def exec(start_state: GlobalState, pre_hooks: List[Callable]=None) -> List[GlobalState]:
    states_queue = [start_state]
    states_final = []
    while len(states_queue) > 0:
        global_state_cur = states_queue.pop(0)

        new_states_queue, new_states_final, _ = state_exec(global_state_cur, pre_hooks)
        states_final.extend(new_states_final)
        # 深度优先
        states_queue = new_states_queue + states_queue
    return states_final

def gene_calldata_contraints(call_data: SymbolicCalldata, function_signature: str) -> List[Bool]:
    constraints = [] # Constraints()
    func_hash = function_signature_to_4byte_selector(function_signature)
    for i in range(4):
        constraint =  call_data[i] == symbol_factory.BitVecVal(func_hash[i],8)
        
        constraints.append(constraint)
    return constraints
