import * as vscode from 'vscode';
import { refreshDiagnostics, subscribeToDocumentChanges } from './diagnostics';
import { WizCodeActionProvider } from './codeActions';

let diagnosticCollection: vscode.DiagnosticCollection;

export function activate(context: vscode.ExtensionContext) {
    diagnosticCollection = vscode.languages.createDiagnosticCollection('wiz');
    context.subscriptions.push(diagnosticCollection);

    // Register code action provider for quick fixes
    const codeActionProvider = new WizCodeActionProvider();
    const selector = [
        { language: 'python' },
        { language: 'javascript' },
        { language: 'typescript' },
        { language: 'typescriptreact' },
        { language: 'javascriptreact' },
        { language: 'go' },
        { language: 'rust' },
    ];

    for (const sel of selector) {
        context.subscriptions.push(
            vscode.languages.registerCodeActionsProvider(sel, codeActionProvider, {
                providedCodeActionKinds: [vscode.CodeActionKind.QuickFix],
            })
        );
    }

    // Scan on save
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument((document) => {
            const config = vscode.workspace.getConfiguration('wiz');
            if (config.get<boolean>('scanOnSave', true)) {
                refreshDiagnostics(document, diagnosticCollection);
            }
        })
    );

    // Scan active editor on activation
    if (vscode.window.activeTextEditor) {
        refreshDiagnostics(
            vscode.window.activeTextEditor.document,
            diagnosticCollection
        );
    }

    // Scan when switching editors
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor) {
                refreshDiagnostics(editor.document, diagnosticCollection);
            }
        })
    );

    // Manual scan command
    context.subscriptions.push(
        vscode.commands.registerCommand('wiz.scanFile', () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                refreshDiagnostics(editor.document, diagnosticCollection);
                vscode.window.showInformationMessage('Wiz: Scan complete');
            }
        })
    );

    // Workspace scan command
    context.subscriptions.push(
        vscode.commands.registerCommand('wiz.scanWorkspace', async () => {
            const folders = vscode.workspace.workspaceFolders;
            if (!folders) {
                vscode.window.showWarningMessage('No workspace folder open');
                return;
            }
            vscode.window.showInformationMessage('Wiz: Scanning workspace...');
            for (const folder of folders) {
                // Scan each open document in the workspace
                for (const doc of vscode.workspace.textDocuments) {
                    if (doc.uri.fsPath.startsWith(folder.uri.fsPath)) {
                        await refreshDiagnostics(doc, diagnosticCollection);
                    }
                }
            }
            vscode.window.showInformationMessage('Wiz: Workspace scan complete');
        })
    );
}

export function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.dispose();
    }
}
