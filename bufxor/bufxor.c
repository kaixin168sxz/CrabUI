// bufxor.c
/*
Copyright (c) 2025 kaixin168sxz
*/

#include "py/dynruntime.h"

// xor(out: bytearray, a: bytes, b: bytes)
// 原地 XOR：out[i] = a[i] ^ b[i]
static mp_obj_t bufxor_xor(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_buffer_info_t a_buf, b_buf;
    mp_get_buffer_raise(a_obj, &a_buf, MP_BUFFER_READ);
    mp_get_buffer_raise(b_obj, &b_buf, MP_BUFFER_READ);

    uint8_t *a = (uint8_t*)a_buf.buf;
    const uint8_t *b = (const uint8_t*)b_buf.buf;

    for (size_t i = 0; i < a_buf.len; i++) {
        a[i] = a[i] ^ b[i];
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(bufxor_xor_obj, bufxor_xor);

// 模块初始化函数（入口点）
mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY

    // 设置模块名
    mp_store_global(MP_QSTR___name__, MP_OBJ_NEW_QSTR(MP_QSTR_bufxor));

    // 导出函数：bufxor.xor = ...
    mp_store_global(MP_QSTR_xor, MP_OBJ_FROM_PTR(&bufxor_xor_obj));

    MP_DYNRUNTIME_INIT_EXIT
}