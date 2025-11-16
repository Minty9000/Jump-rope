def smallest(graph,start,goal):
    n=len(graph)
    visited=[float('inf')]*n
    visited[start]=0
    queue=[graph[start]]
    while queue:
        node=queue.pop(0)
        for neighbor in node:
            value=visited[node[0]]+neighbor[1]
            if value<visited[neighbor[0]]:
                visited[neighbor[0]]=value
                queue.append(graph[neighbor[0]])
    return visited[goal]

