import inspect

import pytracer.core.wrapper.cache as wrapper_cache
from pytracer.utils.log import get_logger
from pytracer.utils.singleton import Counter

logger = get_logger()

is_wrapper_attr = "__Pytracer_visited__"

elements = Counter()


class Binding:

    def __init__(self, function, *args, **kwargs):
        try:
            sig = inspect.signature(function)
            self._bind_initializer(sig, *args, **kwargs)
        except ValueError:
            self._default_initializer(*args, **kwargs)

    def _bind_initializer(self, sig, *args, **kwargs):
        # Remove default kwarg that are present in *args
        # Cause error if the same arg is provided twice
        for name, arg in sig.parameters.items():
            if name in kwargs:
                if arg.default == kwargs[name]:
                    kwargs.pop(name)
        bind = sig.bind(*args, **kwargs)
        self.arguments = bind.arguments
        self.args = bind.args
        self.kwargs = bind.kwargs

    def _default_initializer(self, *args, **kwargs):
        self.arguments = {
            **{f"Arg{i}": x for i, x in enumerate(args)}, **kwargs}
        self.args = args
        self.kwargs = kwargs


def format_output(outputs):
    if isinstance(outputs, dict):
        _outputs = outputs
    elif isinstance(outputs, tuple):
        _outputs = {f"Ret{i}": o for i, o in enumerate(outputs)}
    else:
        _outputs = {"Ret": outputs}
    return _outputs
# Generic wrapper


def wrapper(self,
            function,
            function_module,
            function_name,
            *args, **kwargs):

    inputs = Binding(function, *args, **kwargs)

    stack = self.backtrace()
    if hasattr(function, is_wrapper_attr):
        logger.error(f"Function {function} is wrapped itself")

    time = elements()

    self.inputs(time=time,
                module_name=function_module,
                function_name=function_name,
                function=function,
                args=inputs.arguments,
                backtrace=stack)

    outputs = function(*inputs.args, **inputs.kwargs)
    _outputs = format_output(outputs)

    self.outputs(time=time,
                 module_name=function_module,
                 function_name=function_name,
                 function=function,
                 args=_outputs,
                 backtrace=stack)

    return outputs

# Wrapper used for modules' functions


def wrapper_function(self,
                     info,
                     *args, **kwargs):

    fid, fmodule, fname = info
    function = wrapper_cache.id_dict[fid]

    bind = Binding(function, *args, **kwargs)
    stack = self.backtrace()

    if hasattr(function, is_wrapper_attr):
        logger.error(f"Function {function} is wrapped itself")

    time = elements()

    self.inputs(time=time,
                module_name=fmodule,
                function_name=fname,
                function=function,
                args=bind.arguments,
                backtrace=stack)

    outputs = function(*bind.args, **bind.kwargs)
    _outputs = format_output(outputs)

    self.outputs(time=time,
                 module_name=fmodule,
                 function_name=fname,
                 function=function,
                 args=_outputs,
                 backtrace=stack)

    return outputs

# Wrapper used for instances


def wrapper_instance(self, instance, *args, **kwargs):

    function = instance
    fname = getattr(function, "__name__", "")
    fmodule = getattr(function, "__module__", "")
    if not fmodule and hasattr(fmodule, "__class__"):
        fmodule = getattr(function.__class__, "__module__")

    return wrapper(self,
                   function, fmodule, fname,
                   *args, **kwargs)

# Wrapper used for classes


def isstatic(function):
    try:
        sig = inspect.signature(function)
        return 'self' in sig.parameters.keys()
    except ValueError:
        return False


def wrapper_class(self, info, *args, **kwargs):

    fid, fmodule, fname = info
    function = wrapper_cache.id_dict[fid]
    bind = Binding(function, *args, **kwargs)
    stack = self.backtrace()

    if hasattr(function, is_wrapper_attr):
        logger.error(f"Function {function} {dir(function)} is wrapped itself")

    time = elements()

    self.inputs(time=time,
                module_name=fmodule,
                function_name=fname,
                function=function,
                args=bind.arguments,
                backtrace=stack)

    try:
        outputs = function(*bind.args, **bind.kwargs)
    except TypeError:
        outputs = function(*(bind.args[1:]), **bind.kwargs)

    _outputs = format_output(outputs)

    self.outputs(time=time,
                 module_name=fmodule,
                 function_name=fname,
                 function=function,
                 args=_outputs,
                 backtrace=stack)

    return outputs


def get_ufunc_inputs_type(inputs):
    import numpy as np
    inputs_type = []

    for input_ in inputs:
        if np.isscalar(input_):
            inputs_type.append(np.dtype(type(input_)))
        elif np.issubdtype(input_, np.ndarray):
            inputs_type.append(input_.dtype)
        else:
            inputs_type.append(np.ndarray(input_).dtype)

    return inputs_type


def get_ufunc_output_type(args_type, sig_types):
    import numpy as np

    inputs_sym = "".join([arg_type.char for arg_type in args_type])
    for sig_type in sig_types:
        if sig_type.startswith(inputs_sym):
            return sig_type[sig_type.find("->")+2:]

    # The inputs types are not in the signatures of the function
    # We need to find a safe casting
    for sig_type in sig_types:
        return_pos = sig_type.find("->")
        input_type = sig_type[:return_pos]
        output_type = sig_type[return_pos+2:]

        casted_inputs_type = ""
        for i, ity in enumerate(input_type):
            casted_inputs_type = ""
            if np.can_cast(inputs_sym[i], ity):
                casted_inputs_type += ity
            else:
                casted_inputs_type = ""
                break

        if casted_inputs_type != "":
            logger.debug(
                f"Find casting rule {casted_inputs_type} for {inputs_sym}")
            return output_type

    logger.error(
        f"Cannot find suitable casting rule for {args_type} {sig_types}")

    return None

# Special wrapper used for numpy ufunc functions
# Ufunc are base types


def wrapper_ufunc(self, function, *args, **kwargs):

    fname = getattr(function, "__name__", "")
    fmodule = getattr(function, "__module__", "")
    if not fmodule and hasattr(fmodule, "__class__"):
        fmodule = getattr(function.__class__, "__module__")

    inputs = Binding(function, *args, **kwargs)
    stack = self.backtrace()

    time = elements()

    self.inputs(time=time,
                module_name=fmodule,
                function_name=fname,
                function=function,
                args=inputs.arguments,
                backtrace=stack)

    outputs = function(*inputs.args, **inputs.kwargs)

    inputs_type = None
    outputs_type = None
    if args:
        inputs_type = get_ufunc_inputs_type(args)
        outputs_type = get_ufunc_output_type(inputs_type, function.types)
        outputs = outputs.astype(outputs_type)

    _outputs = format_output(outputs)

    self.outputs(time=time,
                 module_name=fmodule,
                 function_name=fname,
                 function=function,
                 args=_outputs,
                 backtrace=stack)

    return outputs
