#define WIN32_LEAN_AND_MEAN
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <windows.h>
#include <winsock2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#pragma comment(lib, "ws2_32.lib")

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("Usage: test_issue_1 <server_exe> <cli_exe>\n");
        return 1;
    }
    
    char *server_exe = argv[1];
    char *cli_exe = argv[2];
    
    // Open log file with inheritance to capture server stdout/stderr
    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = NULL;
    sa.bInheritHandle = TRUE;
    
    HANDLE hLogFile = CreateFileA("server_test.log",
                                  GENERIC_WRITE,
                                  FILE_SHARE_READ | FILE_SHARE_WRITE,
                                  &sa,
                                  CREATE_ALWAYS,
                                  FILE_ATTRIBUTE_NORMAL,
                                  NULL);
    if (hLogFile == INVALID_HANDLE_VALUE) {
        printf("Failed to create log file.\n");
        return 1;
    }

    // Start server process
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags |= STARTF_USESTDHANDLES;
    si.hStdInput = NULL;
    si.hStdError = hLogFile;
    si.hStdOutput = hLogFile;
    ZeroMemory(&pi, sizeof(pi));

    char cmdline[2048];
    snprintf(cmdline, sizeof(cmdline), "\"%s\" --port 16379 --maxclients 10000 --save \"\"", server_exe);

    printf("Testing with server: %s\n", server_exe);
    if (!CreateProcessA(NULL, cmdline, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        printf("Failed to start server process. Error: %lu\n", GetLastError());
        CloseHandle(hLogFile);
        return 1;
    }

    printf("Waiting 2s for startup...\n");
    Sleep(2000);

    // Check if crashed
    DWORD exitCode;
    if (GetExitCodeProcess(pi.hProcess, &exitCode) && exitCode != STILL_ACTIVE) {
        printf("Server crashed on startup.\n");
        CloseHandle(hLogFile);
        return 1;
    }

    // Run CLI for BGSAVE
    printf("Sending BGSAVE...\n");
    char cli_cmdline[2048];
    snprintf(cli_cmdline, sizeof(cli_cmdline), "\"%s\" -p 16379 BGSAVE", cli_exe);
    
    STARTUPINFOA cli_si;
    PROCESS_INFORMATION cli_pi;
    ZeroMemory(&cli_si, sizeof(cli_si));
    cli_si.cb = sizeof(cli_si);
    ZeroMemory(&cli_pi, sizeof(cli_pi));
    
    if (CreateProcessA(NULL, cli_cmdline, NULL, NULL, FALSE, 0, NULL, NULL, &cli_si, &cli_pi)) {
        WaitForSingleObject(cli_pi.hProcess, 5000);
        CloseHandle(cli_pi.hProcess);
        CloseHandle(cli_pi.hThread);
    } else {
        printf("Failed to start CLI process.\n");
    }

    printf("Waiting 2s...\n");
    Sleep(2000);

    // Connect 10 sockets
    printf("Connecting 10 sockets to trigger accept queue...\n");
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2,2), &wsaData);
    
    SOCKET sockets[10];
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(16379);
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    for (int i=0; i<10; i++) {
        sockets[i] = socket(AF_INET, SOCK_STREAM, 0);
        connect(sockets[i], (struct sockaddr*)&addr, sizeof(addr));
    }

    Sleep(1000);

    // Terminate server
    printf("Terminating server...\n");
    TerminateProcess(pi.hProcess, 0);
    WaitForSingleObject(pi.hProcess, 3000);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    
    // We must close our handle to the log file so we can read it
    CloseHandle(hLogFile);
    
    // Cleanup sockets
    for(int i=0; i<10; i++) closesocket(sockets[i]);
    WSACleanup();
    
    // Read log file
    FILE *f = fopen("server_test.log", "rb");
    if (!f) {
        printf("Failed to open server_test.log for reading.\n");
        return 1;
    }
    
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *logs = (char*)malloc(fsize + 1);
    if (!logs) {
        printf("Failed to allocate memory for logs.\n");
        fclose(f);
        return 1;
    }
    fread(logs, 1, fsize, f);
    logs[fsize] = 0;
    fclose(f);

    printf("--- SERVER LOGS ---\n%s\n-------------------\n", logs);

    int errors = 0;
    if (!strstr(logs, "32 bit instance detected")) {
        printf(" - Expected '32 bit instance detected' but it was not found.\n");
        errors++;
    }
    if (!strstr(logs, "Server can't set maximum open files")) {
        printf(" - Expected 'Server can't set maximum open files' error but it was not found.\n");
        errors++;
    }
    if (!strstr(logs, "Background saving error") && !strstr(logs, "CHILD EXIT CODE: 0x1")) {
        printf(" - Expected BGSAVE error/crash but it was not found.\n");
        errors++;
    }
    if (!strstr(logs, "Accepting client connection: Resource temporarily unavailable") && 
        !strstr(logs, "Accepting client connection")) {
        printf(" - Expected spurious 'Accepting client connection' log but it was not found.\n");
        errors++;
    }

    free(logs);

    if (errors == 0) {
        printf("All bugs successfully replicated!\n");
        return 0; // Success
    } else {
        printf("Failed to replicate some bugs.\n");
        return 1; // Failure
    }
}
