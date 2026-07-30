
Sub F_DEMAIS_CLIENTE_2()

    Dim ws As Worksheet
    Dim wsTemp As Worksheet
    Dim nomesPermitidos As Variant
    Dim ordem As Variant
    Dim ultimaColuna As Long
    Dim ultimaLinha As Long
    Dim i As Long, j As Long
    Dim cabecalho As String
    Dim permitido As Boolean
    Dim colEncontrada As Range
    Dim novaColuna As Long
    
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    
    Set ws = ActiveSheet
    
    ' =====================================================
    ' ETAPA 1 - EXCLUIR COLUNAS NÃO PERMITIDAS
    ' =====================================================
    
    nomesPermitidos = Array( _
        "CD ENTREGA", _
        "DT. CHEGADA", _
        "NOTA FISCAL", _
        "CLIENTE", _
        "DESTINATÁRIO - NOME", _
        "DESTINATÁRIO - CIDADE", _
        "PESO INFORMADO", _
        "STATUS TMS", _
        "DT. PRAZO ATUAL", _
        "STATUS PRAZO", _
        "RETORNO FILIAL", _
        "DT. AGENDAMENTO")
    
    ultimaColuna = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    
    For i = ultimaColuna To 1 Step -1
        
        cabecalho = ws.Cells(1, i).Value
        
        ' Limpeza de espaços invisíveis
        cabecalho = Replace(cabecalho, Chr(160), "")
        cabecalho = Replace(cabecalho, vbLf, "")
        cabecalho = Replace(cabecalho, vbCr, "")
        cabecalho = Trim(UCase(cabecalho))
        
        permitido = False
        
        For j = LBound(nomesPermitidos) To UBound(nomesPermitidos)
            If cabecalho = Trim(UCase(nomesPermitidos(j))) Then
                permitido = True
                Exit For
            End If
        Next j
        
        If permitido = False Then
            ws.Columns(i).Delete
        End If
        
    Next i
    
    ' =====================================================
    ' ETAPA 2 - ORGANIZAR COLUNAS NA ORDEM CORRETA
    ' =====================================================
    
    ordem = nomesPermitidos ' Mesma ordem definida acima
    
    Set wsTemp = Worksheets.Add
    
    ultimaLinha = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    novaColuna = 1
    
    For i = LBound(ordem) To UBound(ordem)
        
        Set colEncontrada = ws.Rows(1).Find( _
            What:=ordem(i), _
            LookAt:=xlWhole, _
            MatchCase:=False)
        
        If Not colEncontrada Is Nothing Then
            
            ws.Range(ws.Cells(1, colEncontrada.Column), _
                     ws.Cells(ultimaLinha, colEncontrada.Column)).Copy _
                     wsTemp.Cells(1, novaColuna)
            
            novaColuna = novaColuna + 1
            
        Else
            MsgBox "Cabeçalho não encontrado: " & ordem(i), vbExclamation
        End If
        
    Next i
    
    ' Limpar planilha original
    ws.Cells.Clear
    
    ' Copiar de volta já organizado
    wsTemp.Cells.Copy ws.Cells(1, 1)
    
    ' Excluir temporária
    wsTemp.Delete
    
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    
    MsgBox "Colunas excluídas e organizadas com sucesso!", vbInformation

End Sub
