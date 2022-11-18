#
# TEST.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Helper to unit-test ( name ) functions
#

from CircBuff import CircBuff

def testCircBuff():
    cbuff = CircBuff(8);
    cbuff.append([1, 2, 3, 4])
    print(*cbuff.circ_buff)
    
    cbuff.append([5, 6])
    print(*cbuff.circ_buff)
    print(f"head: {cbuff.buff_head}, tail: {cbuff.buff_tail}")
    
    cbuff.consume(3)
    print(*cbuff.circ_buff)
    print(f"head: {cbuff.buff_head}, tail: {cbuff.buff_tail}")
    
    cbuff.append([7, 8, 9, 10, 11])
    print(*cbuff.circ_buff)
    if not cbuff.append([12]):
        print("Good: cannot append, buffer full")
    
    cbuff.reset()
    if not cbuff.consume(1):
        print("Good: cannot consume, buffer empty")



# MAIN
all_test_funcs = [ testCircBuff ]
num_tests = len(all_test_funcs)

# run all functions
# TODO: add catching and printing exception functionality
print("\nRunning tests...\n");
for i in range(0, num_tests):
    print(f"[{i}]: {all_test_funcs[i].__name__}")
    all_test_funcs[i]()