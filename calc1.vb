
Sub F_DEMAIS_CLIENTE_1()

    Dim nomesPermitidos As Variant
    Dim ultimaColuna As Long
    Dim ultimaLinha As Long
    Dim i As Long
    Dim nomeCabecalho As String
    Dim ws As Worksheet
    Dim celula As Range
    Dim colunasCentralizadas As Variant

    ' === Etapa 1: Definir colunas permitidas ===
    nomesPermitidos = Array( _
        "Nota Fiscal", _
        "Cliente", _
        "Nome Pessoa Visita", _
        "Cidade Pessoa Visita", _
        "Status", _
        "Dt. Prazo Atual", _
        "Dt. Cadastro", _
        "Dt. Agendamento", _
        "Peso Informado", _
        "Sigla Unidade Entrega")

    Set ws = ActiveSheet
    ultimaColuna = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column

    ' === Etapa 2: Excluir colunas não permitidas ===
    For i = ultimaColuna To 1 Step -1
        nomeCabecalho = Trim(ws.Cells(1, i).Value)
        If IsError(Application.Match(nomeCabecalho, nomesPermitidos, 0)) Then
            ws.Columns(i).Delete
        End If
    Next i

    ' === Etapa 2.1: Mover Dt. Agendamento para depois de Peso Informado ===
    Dim cAgendamento As Range, cPesoInfo As Range
    Set cAgendamento = ws.Rows(1).Find("Dt. Agendamento", LookAt:=xlWhole)
    Set cPesoInfo = ws.Rows(1).Find("Peso Informado", LookAt:=xlWhole)

    If Not cAgendamento Is Nothing And Not cPesoInfo Is Nothing Then
        ws.Columns(cAgendamento.Column).Cut
        ws.Columns(cPesoInfo.Column + 1).Insert Shift:=xlToRight
    End If

    ' === Etapa 3: Inserir Retorno Filial ===
    ws.Columns("B").Insert Shift:=xlToRight
    ws.Cells(1, 2).Value = "Retorno Filial"

    ' === Etapa 4: Inserir Prazo ===
    ws.Columns("A").Insert Shift:=xlToRight
    ws.Cells(1, 1).Value = "Prazo"

    ' === Etapa 5: Criar aba RETORNOS ===
    On Error Resume Next
    Sheets.Add(After:=Sheets(Sheets.Count)).Name = "RETORNOS"
    On Error GoTo 0

    ' === Etapa 6: Cabeçalhos RETORNOS ===
    With Sheets("RETORNOS")
        .Cells.Clear
        .Range("A1").Value = "Nota Fiscal"
        .Range("B1").Value = "Retorno Filial"
    End With

    ' === Etapa 7: Limpar "/*" na coluna B ===
    With ws.Columns("B")
        .Replace What:="/*", Replacement:="", LookAt:=xlPart, _
        SearchOrder:=xlByRows, MatchCase:=False
    End With

    ' === Etapa 8: Fórmula coluna C ===
    ultimaLinha = ws.Cells(ws.Rows.Count, "B").End(xlUp).Row
    For i = 2 To ultimaLinha
        ws.Cells(i, "C").FormulaLocal = "=SEERRO(PROCV(B" & i & ";RETORNOS!A:B;2;0);"""")"
    Next i

    ' === Etapa 10: Renomear planilha ===
    On Error Resume Next
    ws.Name = "TMS"
    On Error GoTo 0

    ' === Etapa 12: Centralizar colunas ===
    colunasCentralizadas = Array("B", "K", "I", "J")
    For i = LBound(colunasCentralizadas) To UBound(colunasCentralizadas)
        ws.Columns(colunasCentralizadas(i)).HorizontalAlignment = xlCenter
    Next i

    ' === Etapa 13: Formatar coluna I como data ===
    ws.Columns("I").NumberFormat = "dd/mm/yy"

    ' === Etapa 14: Movimentar colunas ===
    With ws
        Dim cPrazo As Range, cSigla As Range, cPeso As Range
        Dim cStatus As Range, cCadastro As Range
        Dim cNota As Range, cPrazoAtual As Range, cRetorno As Range

        Set cPrazo = .Rows(1).Find("Prazo", LookAt:=xlWhole)
        Set cSigla = .Rows(1).Find("Sigla Unidade Entrega", LookAt:=xlWhole)
        Set cPeso = .Rows(1).Find("Peso Informado", LookAt:=xlWhole)
        Set cStatus = .Rows(1).Find("Status", LookAt:=xlWhole)
        Set cCadastro = .Rows(1).Find("Dt. Cadastro", LookAt:=xlWhole)
        Set cNota = .Rows(1).Find("Nota Fiscal", LookAt:=xlWhole)
        Set cPrazoAtual = .Rows(1).Find("Dt. Prazo Atual", LookAt:=xlWhole)
        Set cRetorno = .Rows(1).Find("Retorno Filial", LookAt:=xlWhole)

        If Not cSigla Is Nothing And Not cPrazo Is Nothing Then
            .Columns(cSigla.Column).Cut
            .Columns(cPrazo.Column).Insert Shift:=xlToRight
        End If

        If Not cPeso Is Nothing And Not cStatus Is Nothing Then
            .Columns(cPeso.Column).Cut
            .Columns(cStatus.Column).Insert Shift:=xlToRight
        End If

        If Not cCadastro Is Nothing And Not cNota Is Nothing Then
            .Columns(cCadastro.Column).Cut
            .Columns(cNota.Column).Insert Shift:=xlToRight
        End If

        If Not cPrazoAtual Is Nothing And Not cStatus Is Nothing Then
            .Columns(cPrazoAtual.Column).Cut
            .Columns(cStatus.Column).Insert Shift:=xlToRight
        End If

        Set cStatus = .Rows(1).Find("Status", LookAt:=xlWhole)
        Set cPrazo = .Rows(1).Find("Prazo", LookAt:=xlWhole)
        If Not cPrazo Is Nothing And Not cStatus Is Nothing Then
            .Columns(cPrazo.Column).Cut
            .Columns(cStatus.Column + 1).Insert Shift:=xlToRight
        End If

        Set cPrazo = .Rows(1).Find("Prazo", LookAt:=xlWhole)
        Set cRetorno = .Rows(1).Find("Retorno Filial", LookAt:=xlWhole)
        If Not cRetorno Is Nothing And Not cPrazo Is Nothing Then
            .Columns(cRetorno.Column).Cut
            .Columns(cPrazo.Column + 1).Insert Shift:=xlToRight
        End If
    End With

    ' === Etapa FINAL: Ajustes finais de cabeçalho ===
    ultimaColuna = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column

    With ws.Rows(1)
        .Replace What:="Sigla Unidade Entrega", Replacement:="CD Entrega", LookAt:=xlWhole
        .Replace What:="Dt. Cadastro", Replacement:="Dt. Chegada", LookAt:=xlWhole
        .Replace What:="Nome Pessoa Visita", Replacement:="Destinatário - Nome", LookAt:=xlWhole
        .Replace What:="Cidade Pessoa Visita", Replacement:="Destinatário - Cidade", LookAt:=xlWhole
        .Replace What:="Prazo", Replacement:="Status Prazo", LookAt:=xlWhole
        .Replace What:="Status", Replacement:="Status TMS", LookAt:=xlWhole
    End With

    Dim cStatusTMS As Range, cPrazoAtualFinal As Range
    Set cStatusTMS = ws.Rows(1).Find("Status TMS", LookAt:=xlWhole)
    Set cPrazoAtualFinal = ws.Rows(1).Find("Dt. Prazo Atual", LookAt:=xlWhole)

    If Not cStatusTMS Is Nothing And Not cPrazoAtualFinal Is Nothing Then
        ws.Columns(cPrazoAtualFinal.Column).Cut
        ws.Columns(cStatusTMS.Column + 1).Insert Shift:=xlToRight
    End If

    ws.Columns("B").NumberFormat = "dd/mm/yy"

    For Each celula In ws.Range(ws.Cells(1, 1), ws.Cells(1, ultimaColuna))
        celula.Interior.Color = RGB(224, 4, 43)
        celula.Font.Color = RGB(255, 254, 254)
        celula.Font.Bold = True
    Next celula
  ' === PADRONIZAR CABEÇALHOS EM MAIÚSCULO ===
    Dim cab As Range
    For Each cab In ws.Rows(1).Cells
        Select Case Trim(cab.Value)
            Case "CD Entrega": cab.Value = "CD ENTREGA"
            Case "Dt. Chegada": cab.Value = "DT. CHEGADA"
            Case "Nota Fiscal": cab.Value = "NOTA FISCAL"
            Case "Cliente": cab.Value = "CLIENTE"
            Case "Destinatário - Nome": cab.Value = "DESTINATÁRIO - NOME"
            Case "Destinatário - Cidade": cab.Value = "DESTINATÁRIO - CIDADE"
            Case "Peso Informado": cab.Value = "PESO INFORMADO"
            Case "Status TMS": cab.Value = "STATUS TMS"
            Case "Dt. Prazo Atual": cab.Value = "DT. PRAZO ATUAL"
            Case "Status Prazo": cab.Value = "STATUS PRAZO"
            Case "Retorno Filial": cab.Value = "RETORNO FILIAL"
            Case "Dt. Agendamento": cab.Value = "DT. AGENDAMENTO"
        End Select
    Next cab
    ' === Excluir clientes da coluna D ===
    Dim clientesExcluir As Variant
    clientesExcluir = Array( _
    "NINFA INDUSTRIA DE ALIMENTOS LTDA", _
    "MINAS MAIS ALIMENTOS LTDA", _
    "PREDILECTA ALIMENTOS LTDA", _
    "SO FRUTA ALIMENTOS LTDA", _
    "STELLA DORO ALIMENTOS LTDA")
    
    With ws
    .Rows(1).AutoFilter Field:=4, Criteria1:=clientesExcluir, Operator:=xlFilterValues
    On Error Resume Next
    .Range("A2:A" & .Cells(.Rows.Count, "D").End(xlUp).Row).SpecialCells(xlCellTypeVisible).EntireRow.Delete
    On Error GoTo 0
    If .AutoFilterMode Then .AutoFilterMode = False
    End With
    
    ' === Aplicar filtro e congelar ===
    ws.Rows(1).AutoFilter
    ws.Activate
    ws.Rows("2:2").Select
    ActiveWindow.FreezePanes = True

    ' === Classificação de Data e fórmula ===
    Dim dtHoje As Date, cellDate As Variant
    ultimaLinha = ws.Cells(ws.Rows.Count, "I").End(xlUp).Row
    dtHoje = Date

    For i = 2 To ultimaLinha
        If IsDate(ws.Cells(i, "I").Value) Then
            cellDate = ws.Cells(i, "I").Value
            Select Case cellDate
                Case Is < dtHoje
                    ws.Cells(i, "J").Value = "01_ATRASO"
                Case dtHoje
                    ws.Cells(i, "J").Value = "02_VENCENDO HOJE"
                Case dtHoje + 1
                    ws.Cells(i, "J").Value = "03_VENCENDO AMANHÃ"
                Case dtHoje + 2
                    ws.Cells(i, "J").Value = "04_DEPOIS DE AMANHÃ"
                Case Is > dtHoje + 2
                    ws.Cells(i, "J").Value = "05_VENCIMENTO FUTURO"
            End Select
        Else
            ws.Cells(i, "J").Value = ""
        End If
    Next i

    ' === Formatação condicional coluna J ===
    With ws.Range("J2:J" & ultimaLinha)
        .FormatConditions.Delete

        .FormatConditions.Add Type:=xlTextString, String:="01_ATRASO", TextOperator:=xlContains
        With .FormatConditions(.FormatConditions.Count)
            .Interior.Color = RGB(255, 199, 206)
            .Font.Color = RGB(156, 0, 6)
        End With

        .FormatConditions.Add Type:=xlTextString, String:="02_VENCENDO HOJE", TextOperator:=xlContains
        With .FormatConditions(.FormatConditions.Count)
            .Interior.Color = RGB(255, 235, 156)
            .Font.Color = RGB(156, 101, 0)
        End With

        .FormatConditions.Add Type:=xlTextString, String:="03_VENCENDO AMANHÃ", TextOperator:=xlContains
        With .FormatConditions(.FormatConditions.Count)
            .Interior.Color = RGB(204, 229, 255)
            .Font.Color = RGB(0, 51, 153)
        End With

        .FormatConditions.Add Type:=xlTextString, String:="04_DEPOIS DE AMANHÃ", TextOperator:=xlContains
        With .FormatConditions(.FormatConditions.Count)
            .Interior.Color = RGB(230, 230, 250)
            .Font.Color = RGB(75, 0, 130)
        End With

        .FormatConditions.Add Type:=xlTextString, String:="05_VENCIMENTO FUTURO", TextOperator:=xlContains
        With .FormatConditions(.FormatConditions.Count)
            .Interior.Color = RGB(198, 239, 206)
            .Font.Color = RGB(0, 97, 0)
        End With
    End With

    ' === Bordas ===
    Dim ultimaLinhaBordas As Long
    ultimaLinhaBordas = ws.Cells(ws.Rows.Count, "C").End(xlUp).Row

    With ws.Range("A1:K" & ultimaLinhaBordas).Borders
        .LineStyle = xlContinuous
        .Weight = xlThin
        .ColorIndex = 0
    End With

    ' === Copiar formatação da coluna I para a coluna L ===
    With ws
        .Columns("I").Copy
        .Columns("L").PasteSpecial xlPasteFormats
        Application.CutCopyMode = False
    End With

    ' =========================================================
    ' === NOVO BLOCO ADICIONADO (RENOMEAR CABEÇALHOS FIXOS) ===
    ' =========================================================

    ws.Range("A1").Value = "CD ENTREGA"
    ws.Range("B1").Value = "DT. CHEGADA"
    ws.Range("C1").Value = "NOTA FISCAL"
    ws.Range("D1").Value = "CLIENTE"
    ws.Range("E1").Value = "DESTINATÁRIO - NOME"
    ws.Range("F1").Value = "DESTINATÁRIO - CIDADE"
    ws.Range("G1").Value = "PESO INFORMADO"
    ws.Range("H1").Value = "STATUS TMS"
    ws.Range("I1").Value = "DT. PRAZO ATUAL"
    ws.Range("J1").Value = "STATUS PRAZO"
    ws.Range("K1").Value = "RETORNO FILIAL"
    ws.Range("L1").Value = "DT. AGENDAMENTO"

End Sub
