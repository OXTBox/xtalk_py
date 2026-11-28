#!/usr/bin/env python3
"""xtpy_server.py - an MCP server (stdio) with ONLY the xtpy tools (x1-14), none of LIB_MCP's livecode_* tools:
every Claude Code session and helper may have it without driving the one LiveCode. Standard library only.

    python3 -I ~/projects/xtalk_py/mcp/xtpy_server.py
    claude mcp add -s user xtpy -- python3 -I /home/<you>/projects/xtalk_py/mcp/xtpy_server.py   (after the merge)
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/projects/LIB_MCP/python'))
import json                           # noqa: E402
from lib_mcp import mcp_server       # noqa: E402  (its call_tool and reply; its LiveCode tools are not given)

INSTRUCTIONS = ('Hidden xTalk (LiveCode Script) stacks and Vibecode3D games in the Python runtime. Call xtpy_primer '
                'first. Nothing appears on screen; up to 4 stacks open at once; their writes stay in a test folder.')


def serve(tools):
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, id_ = msg.get('method'), msg.get('id')
        if method == 'initialize':
            mcp_server.reply(id_, {'protocolVersion': (msg.get('params') or {}).get('protocolVersion') or '2024-11-05',
                                   'capabilities': {'tools': {}}, 'serverInfo': {'name': 'xtpy', 'version': '0.1.0'},
                                   'instructions': INSTRUCTIONS})
        elif method == 'tools/list':
            mcp_server.reply(id_, {'tools': [{'name': n, 'description': d, 'inputSchema': sc} for n, _, d, sc in tools]})
        elif method == 'tools/call':
            p = msg.get('params') or {}
            content, err = mcp_server.call_tool(tools, p.get('name'), p.get('arguments'))
            mcp_server.reply(id_, {'content': content, 'isError': err})
        elif method == 'ping':
            mcp_server.reply(id_, {})
        elif id_ is not None:
            mcp_server.reply(id_, error={'code': -32601, 'message': 'method not found: %s' % method})


def main():
    if any(a in ('-h', '--help') for a in sys.argv[1:]):
        sys.exit(__doc__)
    spec = importlib.util.spec_from_file_location('xtpy_tools', os.path.join(HERE, 'xtpy_tools.py'))
    pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pack)
    try:
        serve(list(pack.TOOLS))
    finally:
        pack.t_close({'session': 'all'})


if __name__ == '__main__':
    main()
