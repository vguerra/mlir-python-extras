import numpy as np

import mlir_utils.types as T
from mlir_utils.ast.canonicalize import canonicalize
from mlir_utils.context import MLIRContext, mlir_mod_ctx
from mlir_utils.dialects.ext.arith import constant
from mlir_utils.dialects.ext.func import func
from mlir_utils.dialects.ext.scf import canonicalizer as scf, range_ as range
from mlir_utils.runtime.passes import Pipeline, run_pipeline
from mlir_utils.runtime.refbackend import LLVMJITBackend

# you need this to register the memref value caster
# noinspection PyUnresolvedReferences
import mlir_utils.dialects.ext.memref


def setting_memref(ctx: MLIRContext, backend: LLVMJITBackend):
    K = 10
    memref_i64 = T.memref(K, K, T.i64)

    @func
    @canonicalize(using=scf)
    def memfoo(A: memref_i64, B: memref_i64, C: memref_i64):
        one = constant(1)
        two = constant(2)
        if one > two:
            three = constant(3)
        else:
            for i in range(0, K):
                for j in range(0, K):
                    C[i, j] = A[i, j] * B[i, j]

    memfoo.emit()
    # run_pipeline(ctx.module, Pipeline().cse())
    print(ctx.module)

    module = backend.compile(
        ctx.module,
        kernel_name=memfoo.__name__,
        pipeline=Pipeline().bufferize().lower_to_llvm(),
    )

    # windows defaults to int32
    A = np.random.randint(0, 10, (K, K)).astype(np.int64)
    B = np.random.randint(0, 10, (K, K)).astype(np.int64)
    C = np.zeros((K, K), dtype=np.int64)

    backend.load(module).memfoo(A, B, C)
    assert np.array_equal(A * B, C)


with mlir_mod_ctx() as ctx:
    setting_memref(ctx, LLVMJITBackend())