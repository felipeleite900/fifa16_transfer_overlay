//! Injetor da DLL fifa_overlay no processo fifa16.exe.
//!
//! Uso:
//!     fifa_injector.exe [caminho_para_fifa_overlay.dll]
//!
//! Se o caminho não for informado, procura `fifa_overlay.dll` no
//! mesmo diretório do executável do injetor (útil quando ambos os
//! binários são compilados e copiados juntos).

use std::path::PathBuf;

use hudhook::inject::Process;

const TARGET_PROCESS: &str = "fifa16.exe";
const DEFAULT_DLL_NAME: &str = "fifa_overlay.dll";

fn main() {
    let dll_path: PathBuf = match std::env::args().nth(1) {
        Some(arg) => PathBuf::from(arg),
        None => {
            let mut exe_dir = std::env::current_exe().expect("current_exe");
            exe_dir.pop();
            exe_dir.push(DEFAULT_DLL_NAME);
            exe_dir
        }
    };

    let dll_path = dll_path
        .canonicalize()
        .unwrap_or_else(|e| panic!("Não encontrei a DLL em {:?}: {}", dll_path, e));

    println!("[fifa_injector] DLL: {}", dll_path.display());
    println!("[fifa_injector] Procurando processo '{}'...", TARGET_PROCESS);

    let process = Process::by_name(TARGET_PROCESS)
        .unwrap_or_else(|e| panic!("Processo '{}' não encontrado: {}", TARGET_PROCESS, e));

    println!("[fifa_injector] Processo encontrado. Injetando...");

    process
        .inject(dll_path)
        .unwrap_or_else(|e| panic!("Falha ao injetar DLL: {}", e));

    println!("[fifa_injector] DLL injetada com sucesso.");
    println!("[fifa_injector] Log da DLL: {}\\fifa_overlay.log", std::env::temp_dir().display());
}
