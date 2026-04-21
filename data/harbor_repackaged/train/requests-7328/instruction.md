Issue: Endless history: the history contains a self-reference

The history of a requests contains a self-reference to the history owner. The history will be endless.

## Expected Result
If I traverse recursive the complete history of a requests, this will be a finally graph.
The history of a request is a tree without cycles. 

```
R1 (history: 2)
     R2 (no history)
     R3 (no history)
```

## Actual Result
If I traverse recursive the complete history of a requests, the program breaks with recursive error. `RecursionError: maximum recursion depth exceeded while calling a Python object`
The history contains a self-reference to the history owner.

The history of a request is a graph with a cycle.

```
R1 (history: 2)
     R2 (no history)
          R3 (history: 1)
               R3 (history: 1)
                    R3 (history: 1)
                         R3 (history: 1)
                              R3 (history: 1)
                                   ....
```
```
id=140537834271072 history=2
	index=0 id=140537834079136
	index=1 id=140537834080960
id=140537834079136 history=0
id=140537834080960 history=1
	index=0 id=140537834080960
id=140537834080960 history=1
	index=0 id=140537834080960
id=140537834080960 history=1
	index=0 id=140537834080960
id=140537834080960 history=1
	index=0 id=140537834080960

....


id=140537834080960 history=1
	index=0 id=140537834080960
id=140537834080960 history=1
	index=0 id=140537834080960
Traceback (most recent call last):
  File "/Users/andreas/PycharmProjects/cce/main.py", line 12, in <module>
    history(requests.get('https://coord.info/GC8T8E8'))
  File "/Users/andreas/PycharmProjects/cce/main.py", line 9, in history
    history(item)
  File "/Users/andreas/PycharmProjects/cce/main.py", line 9, in history
    history(item)
  File "/Users/andreas/PycharmProjects/cce/main.py", line 9, in history
    history(item)
  [Previous line repeated 993 more times]
  File "/Users/andreas/PycharmProjects/cce/main.py", line 5, in history
    print(f"id

PR: Prevent Response self-reference in redirect history

This PR should address #6295, avoiding the unnecessary addition of the current response in its own redirect history. Ideally, we should remove intermediate `.history` assignment entirely, as `Session.send()` overwrites it on the final response anyway. The intermediary behavior introduces a number of issues both in intuitiveness and a reference explosion delaying the objects being properly cleaned up after use.

That's unfortunately a breaking change we'll have to wait on, but this should fix the immediate issue for now.