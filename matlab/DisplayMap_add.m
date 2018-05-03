function DisplayMap_add(h,BoundariesRadar, IDsRadar,EventsDayRadars)
    global EventsDayRadars2 uihand;
%     addpath('.\HelperFunctions');
  %% Defining parameters and the physics of the model (Sensors from the file loaded below)
    load('RadarsProperties');
    ZoneShape = Sensors{6};
    
    ActivatedRadar=BoundariesRadar(:,3);
    idno=BoundariesRadar(:,4);
    
    
    %% plot crosswalk map
    figure(h);
    %subplot(4,3,5, 'Position', [.52 .05 .1 .5]);
    subplot('Position', [.50 .05 .1 .5]);
    cla();
    
    for i = 1:length(IDsRadar)
        index = find(strcmp( IDsRadar(i), Sensors{1}));
        if ActivatedRadar(index)
            C = [1 0 0];
            %             ActivatedRadar
        else
            C = [0 0 1];
        end
        hold on;
        PlotZone(Sensors{3}{index}', Sensors{4}{index}', ZoneShape, h, C);
        x=Sensors{3}{index};
        if index==7
            x(1)=x(1)+1.5;
        else
            if index==8
                x(1)=x(1)-1.5;
            end
        end
        j=idno(index);
        if j>0
            EventsDayRadars2
            k=EventsDayRadars2(index).label(j);
            disp(k);
        else
            k=1;
        end
        %         if ~isempty(uihand)
        %
        %             for l=1:length(uihand)
        %                 if uihand~=0
        %                     set(uihand(l),'Visible','off');
        %                 end
        %             end
        %             uihand=[];
        %         end
        
        Temp = uicontrol('style','popupmenu',...
            'units','points','Value',k,'Enable','on',...
            'position',[(550+ 13*x(1)) (65+3.2*x(2)) 29 20],...
            'String',{'0-Not Labeled','1 Ped(NS)','1 Ped(SN)','2 Peds (NS)','2 Peds (SN)', '3+ Peds (NS)','3+ Peds (SN)'...
            'Cycle(Walk) (NS)','Cycle(Walk) (SN)','Cycle(Ride) (NS)','Cycle(Ride) (SN)',...
            'Passenger Vehicle (Straight)','Passenger Vehicle (Left)','Passenger Vehicle (Right)','Passenger Vehicle (Stopped)',...
            'Truck/Trailer (Straight)','Truck/Trailer (Left)','Truck/Trailer (Right)','Truck/Trailer (Stopped)',...
            'Bus (Straight)','Bus (Left)', 'Bus (Right)', 'Bus (Stopped', 'Others'},...
            'foregroundcolor','k',...
            'callback',{@tempout,index,j});
        uihand(index)=Temp;
        if ~ActivatedRadar(index)
            set(uihand(index),'Enable','off');
        end
%             Temp(i) = uicontrol('style','popupmenu',...
%                 'units','points','Visible','off',...
%                 'position',[(550+ 13*x(1)) (65+3.2*x(2)) 25 20],...
%                 'String',{'0','1','2','3'},...
%                 'foregroundcolor','k',...
%                 'callback',{@tempout,index,j});
        
    end
%     val = get(Temp,'String')
    
    function tempout(h,evt,index,j)
        global filen;
        str=get(h,'Value')
        disp(str);
        disp(index);
        EventsDayRadars2(index).label(j)=str;
        save(filen,'EventsDayRadars2');
%         delete(h);
%         set(h, 'Visible', 'off');
    end
    
    xlim([0 10]);
    ylim([-10 100]);
    xlabel('x position');
    ylabel('y position');
    
    
    
end