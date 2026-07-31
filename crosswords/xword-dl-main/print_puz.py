import puz

puzname = 'LA Times - 20260626.puz'

#
# Load a puzzle file:
#
p = puz.read(puzname)

#
# Print all clues and their answers
#
clues = p.clue_numbering()

print('Across')
for clue in clues.across:
    print(f'{clue.number}. {clue.text} - {clue.solution}')

print('Down')
for clue in clues.down:
    print(f'{clue.number}. {clue.text} - {clue.solution}')

#
# Print the puzzle grid
#
for row in p.grid():
    print(' '.join(row))

#
# Unlock a puzzle that has a locked solution
#
p.unlock_solution(7844)

# Now print the unscrambed solution grid:
for row in p.solution_grid():
    print(' '.join(row))

#
# Save a puzzle with modifications:
#
p.fill = 'LAMB' + p.fill[:4]
p.save('example.puz')

#
# New! Convert from Across Lite text format to .puz:
#
#p2 = puz.read_text(puzname)
#p2.save('example.puz')
