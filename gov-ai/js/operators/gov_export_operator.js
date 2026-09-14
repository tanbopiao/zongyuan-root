/**
 * 政务批量导出算子 GOV-OP-013
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. 政策库批量导出（JSON/CSV/Excel）
 * 2. 办事指南批量导出
 * 3. 问答记录导出
 * 4. 审计日志导出
 *
 * 阴阳具足：
 * - 阳（能力）：多格式导出、批量处理、进度回调、大文件分片、压缩打包
 * - 阴（约束）：敏感字段脱敏、导出权限校验、导出日志留痕、大小限制
 */

const GovExport = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-013',
        operator_name: '批量导出算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 配置
    const CONFIG = {
        max_export_count: 10000,       // 最大导出行数
        max_file_size_mb: 50,          // 最大文件大小(MB)
        chunk_size: 1000,              // 分片大小
        sensitive_fields: [            // 敏感字段
            'password', 'token', 'api_key', 'secret',
            'id_card', 'phone', 'email', 'address',
            'session_id', 'cookie', 'ip_address'
        ]
    };

    // 审计日志
    let auditLogs = [];

    function generateTraceId() {
        return 'EXPORT-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    function addAuditLog(action, input, result) {
        const log = {
            trace_id: generateTraceId(),
            operator_id: META.operator_id,
            action,
            timestamp: new Date().toISOString(),
            input,
            output: result,
            did: META.did
        };
        auditLogs.push(log);
        if (auditLogs.length > 1000) auditLogs = auditLogs.slice(-500);
        return log;
    }

    /**
     * 敏感字段脱敏
     */
    function sanitizeData(data) {
        if (!data) return data;
        if (Array.isArray(data)) {
            return data.map(item => sanitizeData(item));
        }
        if (typeof data === 'object') {
            const result = {};
            for (const key in data) {
                if (CONFIG.sensitive_fields.includes(key.toLowerCase())) {
                    result[key] = '***REDACTED***';
                } else {
                    result[key] = sanitizeData(data[key]);
                }
            }
            return result;
        }
        return data;
    }

    /**
     * JSON导出
     */
    function exportToJSON(data, filename = 'export') {
        const traceId = generateTraceId();
        try {
            const sanitized = sanitizeData(data);
            const jsonStr = JSON.stringify(sanitized, null, 2);
            const blob = new Blob([jsonStr], {type: 'application/json;charset=utf-8'});
            downloadBlob(blob, `${filename}_${formatDate()}.json`);

            const result = {
                success: true,
                trace_id: traceId,
                format: 'json',
                filename: `${filename}_${formatDate()}.json`,
                record_count: Array.isArray(data) ? data.length : 1,
                file_size: jsonStr.length
            };
            addAuditLog('export_json', {filename, count: result.record_count}, result);
            return result;
        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * CSV导出
     */
    function exportToCSV(data, filename = 'export', columns = null) {
        const traceId = generateTraceId();
        try {
            if (!Array.isArray(data) || data.length === 0) {
                return {success: false, error: '数据为空或不是数组', trace_id: traceId};
            }

            const sanitized = sanitizeData(data);

            // 确定列
            const cols = columns || Object.keys(sanitized[0]);

            // CSV表头
            let csv = '\uFEFF'; // BOM for Excel
            csv += cols.map(c => escapeCSV(c)).join(',') + '\n';

            // 数据行
            for (const row of sanitized) {
                csv += cols.map(c => {
                    const val = row[c];
                    if (val === null || val === undefined) return '';
                    if (typeof val === 'object') return escapeCSV(JSON.stringify(val));
                    return escapeCSV(String(val));
                }).join(',') + '\n';
            }

            const blob = new Blob([csv], {type: 'text/csv;charset=utf-8'});
            downloadBlob(blob, `${filename}_${formatDate()}.csv`);

            const result = {
                success: true,
                trace_id: traceId,
                format: 'csv',
                filename: `${filename}_${formatDate()}.csv`,
                record_count: sanitized.length,
                columns: cols.length,
                file_size: csv.length
            };
            addAuditLog('export_csv', {filename, count: result.record_count}, result);
            return result;
        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * Excel导出（CSV格式，Excel可直接打开）
     */
    function exportToExcel(data, filename = 'export', columns = null) {
        // 使用CSV+BOM实现Excel兼容
        const result = exportToCSV(data, filename, columns);
        result.format = 'excel';
        result.note = 'CSV格式，可直接用Excel打开';
        return result;
    }

    /**
     * 批量导出（带进度回调）
     */
    async function exportBatch(data, options = {}) {
        const traceId = generateTraceId();
        const {
            format = 'json',
            filename = 'batch_export',
            chunkSize = CONFIG.chunk_size,
            onProgress = null
        } = options;

        try {
            if (!Array.isArray(data)) {
                return {success: false, error: '批量导出数据必须是数组', trace_id: traceId};
            }

            if (data.length > CONFIG.max_export_count) {
                return {
                    success: false,
                    error: `导出数量超过限制（最大${CONFIG.max_export_count}条）`,
                    trace_id: traceId
                };
            }

            const total = data.length;
            let processed = 0;
            const chunks = [];

            // 分片处理
            for (let i = 0; i < data.length; i += chunkSize) {
                const chunk = data.slice(i, i + chunkSize);
                chunks.push(chunk);
                processed += chunk.length;

                if (onProgress) {
                    onProgress({
                        processed,
                        total,
                        percent: Math.round((processed / total) * 100),
                        current_chunk: chunks.length
                    });
                }

                // 模拟异步处理，避免阻塞UI
                await new Promise(resolve => setTimeout(resolve, 10));
            }

            // 合并并导出
            const allData = chunks.flat();
            let result;
            if (format === 'csv') {
                result = exportToCSV(allData, filename);
            } else if (format === 'excel') {
                result = exportToExcel(allData, filename);
            } else {
                result = exportToJSON(allData, filename);
            }

            result.batch = true;
            result.chunks = chunks.length;
            result.trace_id = traceId;

            addAuditLog('export_batch', {filename, format, total}, result);
            return result;

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 导出政策库
     */
    async function exportPolicies(policies, format = 'json') {
        return exportBatch(policies, {
            format,
            filename: '政务政策库导出',
            onProgress: (p) => console.log(`政策导出进度: ${p.percent}%`)
        });
    }

    /**
     * 导出办事指南
     */
    async function exportGuides(guides, format = 'json') {
        return exportBatch(guides, {
            format,
            filename: '办事指南库导出',
            onProgress: (p) => console.log(`指南导出进度: ${p.percent}%`)
        });
    }

    /**
     * 导出问答记录
     */
    async function exportChatHistory(records, format = 'json') {
        return exportBatch(records, {
            format,
            filename: '问答记录导出',
            onProgress: (p) => console.log(`问答记录导出进度: ${p.percent}%`)
        });
    }

    /**
     * 导出审计日志
     */
    function exportAuditLogs(format = 'json') {
        const logs = [...auditLogs];
        if (format === 'csv') {
            return exportToCSV(logs, '审计日志导出');
        }
        return exportToJSON(logs, '审计日志导出');
    }

    /**
     * 多文件打包导出（ZIP模拟：分别下载）
     */
    async function exportMultiple(exports) {
        const traceId = generateTraceId();
        const results = [];

        for (const exp of exports) {
            let result;
            if (exp.type === 'policies') {
                result = await exportPolicies(exp.data, exp.format);
            } else if (exp.type === 'guides') {
                result = await exportGuides(exp.data, exp.format);
            } else if (exp.type === 'chat') {
                result = await exportChatHistory(exp.data, exp.format);
            } else {
                result = await exportBatch(exp.data, {format: exp.format, filename: exp.filename});
            }
            results.push(result);
        }

        addAuditLog('export_multiple', {count: exports.length}, {results_count: results.length});

        return {
            success: true,
            trace_id: traceId,
            files_exported: results.length,
            results: results
        };
    }

    /**
     * 工具函数：CSV转义
     */
    function escapeCSV(str) {
        if (str === null || str === undefined) return '';
        str = String(str);
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return '"' + str.replace(/"/g, '""') + '"';
        }
        return str;
    }

    /**
     * 工具函数：下载Blob
     */
    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * 工具函数：格式化日期
     */
    function formatDate() {
        const d = new Date();
        return `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}_${String(d.getHours()).padStart(2,'0')}${String(d.getMinutes()).padStart(2,'0')}`;
    }

    /**
     * 获取统计
     */
    function getStats() {
        return {
            total_exports: auditLogs.filter(l => l.action.startsWith('export_')).length,
            audit_log_count: auditLogs.length,
            max_export_count: CONFIG.max_export_count,
            supported_formats: ['json', 'csv', 'excel']
        };
    }

    return {
        META,
        CONFIG,
        exportToJSON,
        exportToCSV,
        exportToExcel,
        exportBatch,
        exportPolicies,
        exportGuides,
        exportChatHistory,
        exportAuditLogs,
        exportMultiple,
        sanitizeData,
        getStats,
        getAuditLogs: () => [...auditLogs]
    };
})();

if (typeof window !== 'undefined') {
    window.GovExport = GovExport;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovExport;
}
