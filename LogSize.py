# Caminho do arquivo original
input_file = r"DIRETORIO_DO_LOG_PARA_DIVISAO_EM_LOGS_MENORES"

# Número de partes desejadas
num_parts = 20

# Tamanho total do arquivo (em bytes)
total_size = os.path.getsize(input_file)

# Tamanho alvo por arquivo
part_size = total_size // num_parts

# Diretório de saída
output_dir = os.path.dirname(input_file)

file_index = 1
current_size = 0

# Cria primeiro arquivo
output_file = os.path.join(output_dir, f"ol{file_index}.log")
out = open(output_file, "w", encoding="utf-8", errors="ignore")

with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        line_size = len(line.encode("utf-8"))

        # Se passar do tamanho alvo, troca de arquivo
        if current_size + line_size > part_size and file_index < num_parts:
            out.close()
            file_index += 1
            output_file = os.path.join(output_dir, f"ol{file_index}.log")
            out = open(output_file, "w", encoding="utf-8", errors="ignore")
            current_size = 0

        out.write(line)
        current_size += line_size

out.close()

print("Divisão por linhas concluída com sucesso!")