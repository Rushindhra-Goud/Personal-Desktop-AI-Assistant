with open('assistant.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'user_echo(command)' in line:
        print(i, line.rstrip())