import os
import imp
import inspect
import compileall

def is_plugin(p):
    """Returns True if 'p' is a plugin.

    p: a string representing the filename of a potential plugin file

    """
    return not p.startswith('__init__.py') and p.endswith('.pyc')

def get_modules(plugin_path):
    """Returns a list of compiled plugin modules.

    plugin_path: a string representing the full path to the plugin
                 folder

    """
    modules = []
    compileall.compile_dir(plugin_path, quiet=True)
    plugin_names = [x for x in os.listdir(plugin_path) if is_plugin(x)]
    for p in [os.path.join(plugin_path, x) for x in plugin_names]:
        info = inspect.getmoduleinfo(p)
        if not info:
            continue
        try:
            m = imp.load_compiled(info[0], p)
        except ImportError:
            m = imp.load_source(info[0], p)
        modules.append(m)
    return modules

def extract_module_callables(module):
    """Returns a list of functions contained in a plugin module.

    module: a plugin module.  get_modules returns a list of these.

    """
    functions = []
    for m in [x for x in inspect.getmembers(module) if x[0] != '__builtins__']:
        if inspect.isfunction(m[1]):
            functions.append(m[1])
        elif inspect.isclass(m[1]) and hasattr(m[1], '__call__'):
            f = lambda event, zserv: m[1](event, zserv)()
            f.__name__ = m[0]
            functions.append(f)
    return functions

def get_plugins(plugin_path):
    """Returns a list of plugin functions.

    plugin_path: a string representing the full path to the plugin
                 folder

    """
    plugins = []
    for module in get_modules(plugin_path):
        plugins.extend(extract_module_callables(module))
    return plugins

