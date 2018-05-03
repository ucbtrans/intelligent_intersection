function PlotZone(ZoneCenter, ZoneDir, ZoneShape, h, C)
% ZoneShape(1) = 1 if ellipse, =2 if rectangle
% ZoneShape(2) = semi-axis along detector direction
% ZoneShape(3) = semi-axis orthogonal to detector direction

    shape = ZoneShape(1);
    AxisDir = ZoneShape(2);
    AxisOrth = ZoneShape(3);
    
    if isempty(C)
        C = get(h, 'colororder');
    end
    
    if shape == 1
        hold on;
        ellipse(AxisDir, AxisOrth, atan(ZoneDir(2)/ZoneDir(1)), ZoneCenter(1), ZoneCenter(2),C);
        
    elseif shape == 2
        hold on;
        Orth = [-ZoneDir(2); ZoneDir(1)];
        Basis = [ZoneDir, Orth];
        iBasis = Basis';
        A = Basis * [-AxisDir; -AxisOrth] + ZoneCenter;
        B = Basis * [AxisDir; -AxisOrth]+ ZoneCenter;
        C = Basis * [AxisDir; AxisOrth]+ ZoneCenter;
        D = Basis * [-AxisDir; AxisOrth]+ ZoneCenter;
        plot(h,[A(1) B(1) C(1) D(1) A(1)],[A(2) B(2) C(2) D(2) A(2)],'color',C);
    end
        

end