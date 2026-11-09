n = 3
grid = [[0.0 for column in range(n)] for row in range(n)]
grid[1][2] = 1.0
print(grid[1][2])
for row in grid:
    print(row)
