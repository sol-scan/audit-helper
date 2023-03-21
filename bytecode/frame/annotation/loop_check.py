from copy import copy, deepcopy
from typing import Mapping, List
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.ethereum.state.annotation import StateAnnotation
from bytecode.frame.annotation.base import get_first_annotation

class LoopCheckAnnotation(StateAnnotation):
    def __init__(self, loop_bound:int, op_trace = None):
        self.op_trace:List[int] = op_trace or []
        self.loop_bound = loop_bound

    def __copy__(self):
        return LoopCheckAnnotation(copy(self.loop_bound), copy(self.op_trace))

    def __deepcopy__(self, _):
        return LoopCheckAnnotation(deepcopy(self.loop_bound), deepcopy(self.op_trace))


class LoopSignal(Exception):
    pass

def calculate_hash(i: int, j: int, trace: List[int]) -> int:
    key = 0
    size = 0
    for itr in range(i, j):
        key |= trace[itr] << ((itr - i) * 8)
        size += 1

    return key

def count_key(trace: List[int], key: int, start: int, size: int) -> int:
    count = 1
    i = start
    while i >= 0:
        if calculate_hash(i, i + size, trace) != key:
            break
        count += 1
        i -= size
    return count

def get_loop_count(trace:List[int]) -> bool:
    found = False
    for i in range(len(trace) - 3, 0, -1):
        if trace[i] == trace[-2] and trace[i + 1] == trace[-1]:
            found = True
            break

    if found:
        key = calculate_hash(i + 1, len(trace) - 1, trace)
        size = len(trace) - i - 2
        count = count_key(trace, key, i + 1, size)
    else:
        count = 0
    return count

def loop_check_pre_hook(global_state: GlobalState):
    annotation:LoopCheckAnnotation = get_first_annotation(global_state,LoopCheckAnnotation)
    if not annotation:
        return
    cur_instr = global_state.get_current_instruction()
    annotation.op_trace.append(cur_instr['address'])
    if cur_instr['opcode'].upper() != 'JUMPDEST':
        return
    count = get_loop_count(annotation.op_trace)
    if count > annotation.loop_bound:
        raise LoopSignal
        

def inject_loop_check(svm, global_state:GlobalState, loop_bound:int = 2):
    global_state.annotate(LoopCheckAnnotation(loop_bound))
    svm.add_inst_pre_hook(loop_check_pre_hook)
